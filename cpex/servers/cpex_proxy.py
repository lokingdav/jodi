import json
from pydantic import BaseModel
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse

from cpex.crypto import groupsig
from cpex.models import cache, iwf
from cpex import config
from cpex.prototype.scripts import setup

from cpex.helpers import mylogging

mylogging.init_mylogger('cpex_proxy', 'logs/cpex-proxy.log')
cache.set_client(cache.connect())

proxy_params = {
    'gsk': groupsig.get_gsk(),
    'gpk': groupsig.get_gpk(),
    'n_ev': config.n_ev, 
    'n_ms': config.n_ms,
    'fake_proxy': config.FAKE_PROXY,
    'logger': mylogging.mylogger
}

def init_server():
    nodes = setup.get_node_hosts()
    cache.save(key=config.EVALS_KEY, value=json.dumps(nodes.get(config.EVALS_KEY)))
    cache.save(key=config.STORES_KEY, value=json.dumps(nodes.get(config.STORES_KEY)))
    return FastAPI(title="CPEX Proxy API")

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
    proxy = iwf.CpexIWF(proxy_params)
    await proxy.cpex_publish(src=req.src, dst=req.dst, token=req.passport)
    return success_response()

@app.get("/retrieve/{src}/{dst}")
async def oob_proxy_retrieve(src: str, dst: str, req: Request):
    proxy = iwf.CpexIWF(proxy_params)
    token = await proxy.cpex_retrieve(src=src, dst=dst)
    return success_response(content={"token": token})

@app.get("/health")
async def health():
    return { "message": "OK", "type": "OOB Proxy", "status": 200 }