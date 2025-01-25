from fastapi import FastAPI, status, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json

import cpex.config as config
import cpex.constants as constants
from cpex.models import persistence, cache
from cpex.prototype.stirshaken import stirsetup, verify_service, auth_service
from cpex.prototype.scripts import setup
from cpex.helpers import misc, files, http

tmax = 15
credential = None
cache_client = None

def init_server():
    global credential, cache_client
    cache_client = cache.connect()

    nodes = setup.get_node_hosts()
    if nodes and nodes.get('sti-cps'):
        cache.save(client=cache_client, key=config.CPS_KEY, value=json.dumps(nodes.get('sti-cps')))
        
    credential = persistence.get_credential(name=f'cps_{config.NODE_ID}')
    if not credential:
        credential = stirsetup.issue_cert(name=f'cps_{config.NODE_ID}')

    return FastAPI()
        
class PublishRequest(BaseModel):
    passports: List[str]
    
class RepublishRequest(PublishRequest):
    token: str
    

def authorize_request(authorization: str, passports: List[str] = None) -> dict:
    authorization = authorization.replace("Bearer ", "")
    decoded = verify_service.verify_token(authorization)
    if not decoded or 'passports' not in decoded:
        return None
    if passports and decoded['passports'] != 'sha256-' + misc.base64encode(misc.hash256(passports)):
        return None
    return decoded

def get_record_key(dest: str, orig: str):
    return f'cps.{config.NODE_ID}.{dest}.{orig}'

def success_response(content={"message": "OK"}):
    return JSONResponse(content=content, status_code=status.HTTP_200_OK)

def not_found_response(content={"message": "Not Found"}):
    return JSONResponse(content=content, status_code=status.HTTP_404_NOT_FOUND)

def unauthorized_response(content={"message": "Unauthorized"}):
    return JSONResponse(content=content, status_code=status.HTTP_401_UNAUTHORIZED)

app = init_server()

@app.post("/publish/{dest}/{orig}")
async def publish(dest: str, orig: str, request: PublishRequest, authorization: str = Header(None)):
    # 1. Verify authorization header token attached by the provider
    decoded = authorize_request(authorization, request.passports)
    if not decoded:
        return unauthorized_response()
    
    # 2. Store passports in cache for 15 seconds
    cache.cache_for_seconds(
        client=cache_client,
        key=get_record_key(dest=dest, orig=orig), 
        value=request.passports, 
        seconds=tmax
    )

    repositories = cache.get_other_cpses(client=cache_client)

    if not repositories:
        return success_response()

    # 4. create new requests with payload: orig, dest, passports, token. Token is the authorization header bearer token
    auth = auth_service.AuthService(
        ownerId=config.NODE_ID,
        private_key_pem=credential[constants.PRIV_KEY],
        x5u=config.CERT_REPO_BASE_URL + f'/certs/cps_{config.NODE_ID}'
    )

    reqs = []
        
    for repo in repositories:
        token = auth.authenticate_request(
            action='republish', 
            orig=orig, 
            dest=dest, 
            passports=request.passports, 
            iss=decoded.get('iss'), 
            aud=repo.get('fqdn')
        )
        reqs.append({
            'url': repo.get('url') + f'/republish/{dest}/{orig}',
            'data': {
                'passports': request.passports,
                'token': authorization
            },
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        })
    
    # 5. Send requests to all repositories
    responses = await http.posts(reqs)
    return success_response()

@app.post("/republish/{dest}/{orig}")
async def republish(dest: str, orig: str, request: RepublishRequest, authorization: str = Header(None)):
    # 1. Verify authorization header token attached by the provider
    decoded = authorize_request(authorization, request.passports)
    if not decoded:
        return unauthorized_response()
    
    # 2. Store passports in cache for 15 seconds
    cache.cache_for_seconds(
        client=cache_client,
        key=get_record_key(dest=dest, orig=orig), 
        value=request.passports, 
        seconds=tmax
    )

    return success_response()

@app.get("/retrieve/{dest}/{orig}")
async def republish(dest: str, orig: str, authorization: str = Header(None)):
    # 1. Verify authorization header token attached by the provider
    decoded = authorize_request(authorization)
    if not decoded:
        return unauthorized_response()
    
    # 2. Retrieve passports from cache
    passports = cache.find(
        client=cache_client,
        key=get_record_key(dest=dest, orig=orig), 
        dtype=dict
    )

    if not passports:
        return not_found_response()
    
    return success_response(content=passports)

@app.get("/health")
async def health():
    return {
        "CPS ID": config.NODE_ID,
        "message": "OK", 
        "status": 200
    }