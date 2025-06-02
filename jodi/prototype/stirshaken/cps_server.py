from fastapi import FastAPI, status, Header, Request
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json, os, random

import jodi.config as config
import jodi.constants as constants
from jodi.models import cache
from jodi.prototype.stirshaken import stirsetup, verify_service, auth_service, certs
from jodi.prototype.scripts import setup
from jodi.helpers import misc, http, mylogging

X5U = None
MY_CRED = None
BASE_CACHE_KEY = f'cps:{config.NODE_FQDN}'
OTHER_CPSs = f'{BASE_CACHE_KEY}:{config.CPS_KEY}'

mylogging.init_mylogger(name='cps_logs', filename=f'logs/cps_server.log')

class PublishRequest(BaseModel):
    passports: List[str]
    
class RepublishRequest(PublishRequest):
    token: str
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    keep_alive_session = http.create_session()
    http.set_session(keep_alive_session)
    yield
    await keep_alive_session.close()

def init_server():
    global MY_CRED, X5U
    
    cache.set_client(cache.connect())
    
    nodes = setup.get_node_hosts()
    if config.CPS_KEY in nodes:
        cache.save(key=OTHER_CPSs, value=json.dumps(nodes.get(config.CPS_KEY)))

    MY_CRED, allcerts = stirsetup.load_certs()
    certs.set_certificate_repository(allcerts)
    X5U = f'http://{config.NODE_IP}:{config.CR_PORT}/certs/' + MY_CRED['id']

    if config.USE_LOCAL_CERT_REPO:
        cache.save_certificates(allcerts)

    return FastAPI(title="CPS API", lifespan=lifespan)

async def authorize_request(authorization: str, passports: List[str] = None) -> dict:
    # mylogging.mylogger.debug(f"{os.getpid()}: Authorizing request")
    authorization = authorization.replace("Bearer ", "")
    decoded = await verify_service.verify_token(authorization)
    # mylogging.mylogger.debug(f"{os.getpid()}: Decoded token: {decoded}")
    if not decoded or 'passports' not in decoded:
        return None
    if passports and decoded['passports'] != 'sha256-' + misc.base64encode(misc.hash256(passports)):
        return None
    return decoded

def get_record_key(dest: str, orig: str):
    return f'{BASE_CACHE_KEY}:{dest}:{orig}'

def success_response(content={"message": "OK"}):
    return JSONResponse(content=content, status_code=status.HTTP_200_OK)

def not_found_response(content={"message": "Not Found"}):
    return JSONResponse(content=content, status_code=status.HTTP_404_NOT_FOUND)

def unauthorized_response(content={"message": "Unauthorized"}):
    return JSONResponse(content=content, status_code=status.HTTP_401_UNAUTHORIZED)

async def do_republish(dest: str, orig: str, request: PublishRequest, authorization: str, decoded: dict):
    mylogging.mylogger.debug(f"{os.getpid()}: Republish started for {orig} to {dest}")
    
    repositories = cache.get_other_cpses(key=OTHER_CPSs)
    
    if not repositories:
        mylogging.mylogger.debug(f"{os.getpid()}: No other CPS found")
        return success_response()
    else:
        mylogging.mylogger.debug(f"{os.getpid()}: Found {len(repositories)} other CPS")

    authService = auth_service.AuthService(
        ownerId=config.NODE_FQDN,
        private_key_pem=MY_CRED[constants.PRIV_KEY],
        x5u=X5U
    )
    # mylogging.mylogger.debug(f"{os.getpid()}: AuthService initialized")

    reqs = []
        
    for repo in repositories:
        token = authService.authenticate_request(
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
    
    mylogging.mylogger.debug(f"{os.getpid()}: Sending republish requests: {[r['url'] for r in reqs]}")
    responses = await http.posts(reqs)
    mylogging.mylogger.debug(f"{os.getpid()}: Republished responses: {responses}")

app = init_server()

@app.post("/publish/{dest}/{orig}")
async def handle_publish_req(dest: str, orig: str, request: PublishRequest, authorization: str = Header(None)):
    mylogging.mylogger.debug(f"{os.getpid()}: PUBLISH request: src={orig},  dst={dest}, passports={request.passports}")
    
    decoded = await authorize_request(authorization, request.passports)
    if not decoded:
        # mylogging.mylogger.error(f"{os.getpid()}: Unauthorized request")
        return unauthorized_response()
    
    mylogging.mylogger.debug(f"{os.getpid()}: Caching Passports")

    cache.cache_for_seconds(
        key=get_record_key(dest=dest, orig=orig), 
        value=request.passports, 
        seconds=config.T_MAX_SECONDS
    )
    
    await do_republish(
        dest=dest, 
        orig=orig, 
        request=request, 
        authorization=authorization, 
        decoded=decoded
    )

    return success_response()

@app.post("/republish/{dest}/{orig}")
async def handle_republish_req(dest: str, orig: str, request: RepublishRequest, authorization: str = Header(None)):
    mylogging.mylogger.debug(f"{os.getpid()}: REPUBLISH request: src={orig},  dst={dest}, passports={request.passports}")
    
    decoded = await authorize_request(authorization, request.passports)
    if not decoded:
        # mylogging.mylogger.error(f"{os.getpid()}: REPUBLISH request unauthorized")
        return unauthorized_response()
    
    mylogging.mylogger.debug(f"Passports key: {get_record_key(dest=dest, orig=orig)}")
    
    cache.cache_for_seconds(
        key=get_record_key(dest=dest, orig=orig), 
        value=request.passports, 
        seconds=config.T_MAX_SECONDS
    )
    # mylogging.mylogger.debug(f"{os.getpid()}: Passports cached")
    
    return success_response()

@app.get("/retrieve/{dest}/{orig}")
async def handle_retrieve_req(dest: str, orig: str, authorization: str = Header(None)):
    mylogging.mylogger.debug(f"{os.getpid()}: RETRIEVE request from, src={orig},  dst={dest}")
    
    decoded = await authorize_request(authorization)
    if not decoded:
        mylogging.mylogger.error(f"{os.getpid()}: RETRIEVE request unauthorized")
        return unauthorized_response()
    
    mylogging.mylogger.debug(f"Passports key: {get_record_key(dest=dest, orig=orig)}")
    passports = cache.find(
        key=get_record_key(dest=dest, orig=orig), 
        dtype=dict
    )

    if not passports:
        mylogging.mylogger.error(f"{os.getpid()}: Passports not found for RETRIEVE request")
        return not_found_response()

    mylogging.mylogger.debug(f"{os.getpid()}: Passports sent for RETRIEVE request")
    return success_response(content=passports)

@app.get("/health")
async def handle_health_req():
    return {
        "Status": 200,
        "Message": "OK", 
        "Node": {
            "IP": config.NODE_IP,
            "PORT": config.NODE_PORT,
            "FQDN": config.NODE_FQDN,
            "X5U": X5U
        },
        "Config": {
            "T_MAX_SECONDS": config.T_MAX_SECONDS,
            "BASE_CACHE_KEY": BASE_CACHE_KEY
        },
        "Others": [n['fqdn'] for n in cache.get_other_cpses(OTHER_CPSs)]
    }