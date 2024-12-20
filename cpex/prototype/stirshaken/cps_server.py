from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

import cpex.config as config
from cpex.models import persistence
from cpex.prototype.stirshaken import stirsetup

credential = None

def init_server():
    global credential
    credential = persistence.get_credential(name=f'cps_{config.REPO_ID}')
    if not credential:
        credential = stirsetup.issue_cert(name=f'cps_{config.REPO_ID}')
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
        "REPO_ID": config.REPO_ID,
        "message": "OK", 
        "status": 200
    }