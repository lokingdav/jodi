import json
from pydantic import BaseModel
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from cpex.crypto import groupsig, billing
from cpex.models import cache, iwf
from cpex import config
from cpex.prototype.scripts import setup
from cpex.helpers import mylogging, http

mylogging.init_mylogger('jodi_proxy', 'logs/jodi-proxy.log')
cache.set_client(cache.connect())

metrics_logger = mylogging.init_logger(
    name='jodi_proxy_metrics',
    filename=f'logs/jodi_proxy_metrics.log',
    level=mylogging.logging.INFO,
    formatter=None
)

proxy_params = {
    'gsk': groupsig.get_gsk(),
    'gpk': groupsig.get_gpk(),
    'n_ev': config.n_ev, 
    'n_ms': config.n_ms,
    'fake_proxy': config.FAKE_PROXY,
    'logger': mylogging.mylogger,
    'metrics_logger': metrics_logger,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    keep_alive_session = http.create_session()
    http.set_session(keep_alive_session)
    yield
    await keep_alive_session.close()

def init_server():
    nodes = setup.get_node_hosts()
    if nodes.get(config.EVALS_KEY):
        cache.save(key=config.EVALS_KEY, value=json.dumps(nodes.get(config.EVALS_KEY)))
    if nodes.get(config.STORES_KEY):
        cache.save(key=config.STORES_KEY, value=json.dumps(nodes.get(config.STORES_KEY)))
        
    return FastAPI(title="Jodi Proxy API", lifespan=lifespan)

app = init_server()

def success_response(content = {"message": "OK"}):
    return JSONResponse(
        content=content, 
        status_code=status.HTTP_200_OK
    )

def error_response(content = {"_error": "Unprocessable Entity"}):
    return JSONResponse(
        content=content, 
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    
class Publish(BaseModel):
    src: str
    dst: str
    passport: str
    
@app.post("/publish")
async def oob_proxy_publish(req: Publish):
    bt = billing.create_endorsed_token(config.VOPRF_SK)
    proxy = iwf.CpexIWF({**proxy_params, 'bt': bt})
    res = await proxy.cpex_publish(src=req.src, dst=req.dst, token=req.passport)
    if '_error' in res:
        return error_response(content=res)
    return success_response()

@app.get("/retrieve/{src}/{dst}")
async def oob_proxy_retrieve(src: str, dst: str, req: Request):
    bt = billing.create_endorsed_token(config.VOPRF_SK)
    proxy = iwf.CpexIWF({**proxy_params, 'bt': bt})
    token = await proxy.cpex_retrieve(src=src, dst=dst)
    return success_response(content={"token": token})

@app.get("/health")
async def health():
    return {
        "message": "OK",
        "type": "OOB Proxy",
        "status": 200
    }