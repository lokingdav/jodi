from pydantic import BaseModel
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional, Literal

from cpex.crypto import groupsig
from cpex.models import cache, iwf
from cpex import config

cache.set_client(cache.connect())

proxy_params = {
    'gsk': groupsig.get_gsk(),
    'gpk': groupsig.get_gpk(),
    'n_ev': config.n_ev, 
    'n_ms': config.n_ms,
    'fake_proxy': config.FAKE_PROXY
}

app = FastAPI(title="CPEX Proxy API")

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

@app.get("/retrieve")
async def oob_proxy_retrieve(req: Retrieve):
    proxy = iwf.CpexIWF(proxy_params)
    token = await proxy.cpex_retrieve(src=req.src, dst=req.dst)
    return success_response(content={"token": token})

@app.get("/health")
async def health():
    return { "message": "OK", "type": "OOB Proxy", "status": 200 }