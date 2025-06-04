from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import jodi.config as config
from jodi.crypto import groupsig, billing, audit_logging
from jodi.models import cache
from jodi.helpers import misc
from jodi.prototype.stirshaken import certs

cache.set_client(cache.connect())
app = FastAPI()
gpk = groupsig.get_gpk()
isk = certs.get_private_key(config.TEST_ISK)

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
    
def success_response(content):
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
    
    cache.enqueue_log({
        "type": config.LOG_TYPE_PUBLISH,
        "hreq": billing.Utils.to_base64(
            billing.Utils.hash256(bytes(req.idx + req.ctx, 'utf-8'))
        ),
        "tk": req.bt,
        "peers": req.peers,
        "sig": req.sig,
    })
    
    return success_response({
        "message": "Created",
        "sig_r": audit_logging.ecdsa_sign(private_key=isk, data=pp + bb + "ok")
    })
    
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
        res = {"message": "Not Found"}
    else:
        (idx, ctx, sig, bill_h) = value.split('.')
        res = {"idx": idx, "ctx": ctx, "sig": sig, 'bb': bill_h}
    
    log_entry = {
        "type": config.LOG_TYPE_RETRIEVE,
        "hreq": billing.Utils.to_base64(billing.Utils.hash256(bytes(req.idx, 'utf-8'))),
        "hres": billing.Utils.to_base64(billing.Utils.hash256(bytes(misc.stringify(res), 'utf-8'))),
        "tk": req.bt,
        "peers": req.peers,
        "sig": req.sig,
    }
    cache.enqueue_log(log_entry)
    
    res['sig_r'] = audit_logging.ecdsa_sign(private_key=isk, data=log_entry['hreq'] + log_entry['hres'])
    
    if "message" in res:
        return JSONResponse(
            content=res,
            status_code=status.HTTP_404_NOT_FOUND
        )
    else:
        return success_response(res)

@app.get("/health")
async def health():
    return { 
        "Status": 200,
        "Message": "OK", 
        "Type": "Message Store", 
    }