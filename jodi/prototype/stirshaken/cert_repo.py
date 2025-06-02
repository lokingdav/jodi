from fastapi import FastAPI, status, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json, os

import jodi.config as config
import jodi.constants as constants
from jodi.models import cache
from jodi.prototype.stirshaken import stirsetup, verify_service, auth_service, certs
from jodi.prototype.scripts import setup
from jodi.helpers import misc, http, mylogging

certificates = None

mylogging.init_mylogger(
    name='cert_repo_logs', 
    filename=f'logs/cert_repos.log'
)

def init_server():
    global certificates
    certificates = stirsetup.load_certs()[1]
    return FastAPI()

app = init_server()

@app.get("/certs/{key}")
async def handle_get_certificate_req(key: str):
    mylogging.mylogger.debug(f"GET /certs/{key}")
    cert = certificates.get(key)
    if not cert or 'cert' not in cert:
        return JSONResponse(
            content={"message": "Not Found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    return cert['cert']

@app.get("/health")
async def handle_health_req():
    return {
        "Status": 200,
        "Message": "OK", 
        "Type": "STI-Cert-Repo",
        "Node Port": config.NODE_PORT
    }