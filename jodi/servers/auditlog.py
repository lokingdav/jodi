import os, time
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi import Request

from jodi.crypto import audit_logging, groupsig
from jodi.models import cache
from jodi.helpers import mylogging
from jodi import config

mylogging.init_mylogger('auditlog', 'logs/auditlog.log')
cache.set_client(cache.connect())
audit_logging.set_gpk(groupsig.get_gpk())

app = FastAPI()

@app.post("/log")
async def write_log(req: Request):
    content = {"message": "Log entry created successfully"}

    return JSONResponse(
        content=content, 
        status_code=status.HTTP_201_CREATED
    )

@app.get("/health")
async def health():
    return { 
        "Status": 200,
        "Message": "OK", 
        "Type": "Evaluator",
    }