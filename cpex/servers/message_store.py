from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import cpex.config as config
from cpex.crypto import groupsig
from cpex.models import cache

cache.set_client(cache.connect())
app = FastAPI()
gpk = groupsig.get_gpk()

class PublishRequest(BaseModel):
    idx: str
    ctx: str
    sig: str
    
class RetrieveRequest(BaseModel):
    idx: str
    sig: str
    
def unauthorized_response():
    return JSONResponse(
        content={"message": "Unauthorized"},
        status_code=status.HTTP_401_UNAUTHORIZED
    )
    
def success_response(content = {"message": "Created"}):
    return JSONResponse(
        content=content, 
        status_code=status.HTTP_200_OK
    )
    
def get_record_key(idx: str):
    return f"ms:{config.NODE_FQDN}:{idx}"
    
@app.post("/publish")
async def publish(req: PublishRequest):
    if not groupsig.verify(sig=req.sig, msg=req.idx + req.ctx, gpk=gpk):
        return unauthorized_response()
    
    value = req.idx + '.' + req.ctx + '.' + req.sig
    cache.cache_for_seconds(
        key=get_record_key(req.idx), 
        value=value, 
        seconds=config.REC_TTL_SECONDS
    )
    
    return success_response()
    
@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    if not groupsig.verify(sig=req.sig, msg=req.idx, gpk=gpk):
        return unauthorized_response()
    
    value = cache.find(key=get_record_key(req.idx))
    
    if value is None:
        return JSONResponse(
            content={"message": "Not Found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    (idx, ctx, sig) = value.split('.')
    
    return success_response({"idx": idx, "ctx": ctx, "sig": sig})

@app.get("/health")
async def health():
    return { "message": "OK", "type": "Message Store", "status": 200 }