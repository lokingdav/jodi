from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import cpex.config as config
from cpex.crypto import groupsig
from cpex.models import cache

app = FastAPI()

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
    return f"ms:{config.NODE_ID}:{idx}"
    
@app.post("/publish")
async def publish(req: PublishRequest):
    if not groupsig.verify(sig=req.sig, msg=str(req.idx) + str(req.ctx), gpk=config.TGS_GPK):
        return unauthorized_response()
    
    value = str(req.idx) + '.' + str(req.ctx) + '.' + str(req.sig)
    cache.cache_for_seconds(get_record_key(req.idx), value, config.REC_TTL_SECONDS)
    
    return success_response()
    
@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    if not groupsig.verify(req.sig, req.idx, config.TGS_GPK):
        return unauthorized_response()
    
    value = cache.find(get_record_key(req.idx))
    
    if value is None:
        return JSONResponse(
            content={"message": "Not Found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    (idx, ctx, sig) = value.split('.')
    
    return success_response({"idx": idx, "ctx": ctx, "sig": sig})

@app.get("/health")
async def health():
    return { "message": "OK", "status": 200 }