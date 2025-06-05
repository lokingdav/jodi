import os, time
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

from jodi.crypto import audit_logging, groupsig
from jodi.models import cache
from jodi.helpers import mylogging
from jodi import config
from jodi.prototype.stirshaken import certs

mylogging.init_mylogger('auditlog', 'logs/auditlog.log')
cache.set_client(cache.connect())

app = FastAPI()

private_key = certs.get_private_key(config.TEST_ISK)
public_key = certs.get_public_key_from_cert(config.TEST_ICERT)

class Request(BaseModel):
    auth_token: str
    logs: List[dict]

@app.post("/logs")
async def write_log(req: Request):
    if not audit_logging.ecdsa_verify(public_key=public_key, data=req.logs, sigma=req.auth_token):
        return JSONResponse(
            content={"message": "Unauthorized: Invalid signature"}, 
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    cache.enqueue_log({ 'logs': req.logs })
    
    print(req.auth_token, req.logs, flush=True)
    return JSONResponse(
        content={"message": "Successfully logged"}, 
        status_code=status.HTTP_201_CREATED
    )

@app.get("/health")
async def health():
    return { 
        "Status": 200,
        "Message": "OK", 
        "Type": "Audit Log Server",
    }