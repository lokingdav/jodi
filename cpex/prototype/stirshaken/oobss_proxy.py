import json
from pydantic import BaseModel
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse

from cpex.models import cache
from cpex import config
from cpex.prototype.stirshaken.oobss_iwf import OobSSIWF

from cpex.helpers import mylogging

logfile = 'oobss_proxy'
mylogging.init_mylogger(logfile, f'logs/{logfile}.log')
cache.set_client(cache.connect())

proxy_params: dict = {
    'pid': config.OOBSS_PROXY_SPC,
    'cps': { 'fqdn': config.OOBSS_PROXY_CPS_FQDN },
    'cr': { 'sk': config.OOBSS_PROXY_CR_SK, 'x5u': config.OOBSS_PROXY_CR_X5U }
}

def init_server():
    return FastAPI(title="OOB-S/S Proxy API")

app = init_server()

def success_response(content = {"message": "OK"}):
    return JSONResponse(
        content=content, 
        status_code=status.HTTP_200_OK
    )

class Retrieve(BaseModel):
    src: str
    dst: str

class Publish(Retrieve):
    passport: str
    
@app.post("/publish")
async def oob_proxy_publish(req: Publish):
    proxy = OobSSIWF({**proxy_params})
    await proxy.atis_publish_token(
        src=req.src, 
        dst=req.dst, 
        identity=req.passport
    )
    return success_response()

@app.get("/retrieve/{src}/{dst}")
async def oob_proxy_retrieve(src: str, dst: str, req: Request):
    proxy = OobSSIWF({**proxy_params})
    token = await proxy.atis_retrieve_token(src=src, dst=dst)
    return success_response(content={"token": token})

@app.get("/health")
async def health():
    return {
        "message": "OK",
        "type": "OOB Proxy",
        "status": 200
    }
