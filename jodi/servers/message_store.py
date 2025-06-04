from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import jodi.config as config
from jodi.crypto import groupsig, billing
from jodi.models import cache

cache.set_client(cache.connect())
app = FastAPI()
gpk = groupsig.get_gpk()

class PublishRequest(BaseModel):
    idx: str
    ctx: str
    sig: str
    bt: str
    peers: str
    
class RetrieveRequest(BaseModel):
    idx: str
    sig: str
    bt: str
    peers: str
    
def unauthorized_response(content={"message": "Unauthorized"}):
    return JSONResponse(
        content=content,
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
    if not billing.verify_token(config.VOPRF_VK, req.bt):
        return unauthorized_response({"message": "Invalid billing Token"})
    
    pp = billing.Utils.to_base64(billing.Utils.hash256(bytes(req.idx + req.ctx, 'utf-8')))
    bb = billing.get_billing_hash(req.bt, req.peers)
    
    if not groupsig.verify(sig=req.sig, msg=pp + bb, gpk=gpk):
        return unauthorized_response()
    
    value = req.idx + '.' + req.ctx + '.' + req.sig + '.' + bb
    cache.cache_for_seconds(
        key=get_record_key(req.idx), 
        value=value, 
        seconds=config.T_MAX_SECONDS
    )
    
    return success_response()
    
@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    if not billing.verify_token(config.VOPRF_VK, req.bt):
        return unauthorized_response({"message": "Invalid billing Token"})
    
    pp = billing.Utils.to_base64(billing.Utils.hash256(bytes(req.idx, 'utf-8')))
    bb = billing.get_billing_hash(req.bt, req.peers)
    
    if not groupsig.verify(sig=req.sig, msg=pp + bb, gpk=gpk):
        return unauthorized_response()
    
    value = cache.find(key=get_record_key(req.idx))
    
    if value is None:
        return JSONResponse(
            content={"message": "Not Found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    (idx, ctx, sig, bill_h) = value.split('.')
    
    return success_response({"idx": idx, "ctx": ctx, "sig": sig, 'bh': bill_h})

@app.get("/health")
async def health():
    cache.enqueue_log({
        "type": config.LOG_TYPE_HEALTH,
        "msg": "Message Store is healthy"
    })
    return { 
        "Status": 200,
        "Message": "OK", 
        "Type": "Message Store", 
    }