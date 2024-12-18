from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import cpex.config as config

import cpex.prototype.stirshaken.certs as sti_certs
import cpex.helpers.files as files
import cpex.constants as constants

conf = None
certs_file = config.CONF_DIR + f'/cps.{config.CPS_ID}.certs.json'

def init_server():
    global conf
    conf = files.read_json(certs_file)
    if not conf:
        cert, (sk, csr) = None, sti_certs.client_keygen(name=f'cps_{config.CPS_ID}')
        while not cert:
            try:
                print("********* Requesting certificate *********")
                cert = sti_certs.request_cert(csr)
            except Exception as e:
                print("Could not obtain certificate from the Certificate Repository.")
                print(e)
        conf = { constants.CERT_KEY: cert, constants.PRIV_KEY: sk }
        files.override_json(fileloc=certs_file, data=conf)
    return FastAPI()
        
class PublishRequest(BaseModel):
    orig: str
    dest: str
    passports: List[str]
    
class RepublishRequest(BaseModel):
    orig: str
    dest: str
    token: str
    
class RetrieveRequest(BaseModel):
    orig: str
    dest: str
    tokens: List[str]

def success_response(content={"message": "OK"}):
    return JSONResponse(content=content, status_code=status.HTTP_200_OK)

def error_response(content={"message": "Sorry, no one is perfect and we are no exception."}):
    return JSONResponse(content=content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

def unauthorized_response(content={"message": "Unauthorized"}):
    return JSONResponse(content=content, status_code=status.HTTP_401_UNAUTHORIZED)

app = init_server()

@app.post("/publish")
async def publish(req: PublishRequest):
    # 1. Verify authorization header token attached by the provider
    # 2. create new requests with payload: orig, dest, passports, token. Token is the authorization header bearer token
    # 3. Broadcast request to the CPS
    return JSONResponse(
        content={"message": "OK"}, 
        status_code=status.HTTP_201_CREATED
    )

@app.post("/republish")
async def republish(req: RepublishRequest):
    return req.model_dump()

@app.post("/retrieve")
async def republish(req: RetrieveRequest):
    return req.model_dump()

@app.get("/health")
async def health():
    return {
        "cps_id": config.CPS_ID,
        "message": "OK", 
        "status": 200
    }