import os, time
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from jodi.crypto import groupsig, oprf, billing, audit_logging
from jodi.models import cache
from jodi.helpers import mylogging, misc
from jodi import config
from jodi.prototype.stirshaken import certs

mylogging.init_mylogger('evaluator', 'logs/evaluator.log')
cache.set_client(cache.connect())
gpk = groupsig.get_gpk()
isk = certs.get_private_key(config.TEST_ISK)

app = FastAPI()

class EvaluateRequest(BaseModel):
    i_k: int
    x: str
    sig: str
    bt: str
    peers: str
    
@app.post("/evaluate")
async def evaluate(req: EvaluateRequest):
    # start_time = time.perf_counter()

    if not billing.verify_token(config.VOPRF_VK, req.bt):
        return JSONResponse(
            content={"message": "Invalid Token"}, 
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    hreq = oprf.Utils.to_base64(oprf.Utils.hash256(
        bytes(req.x + str(req.i_k) + req.bt + req.peers, 'utf-8')
    ))

    if not groupsig.verify(sig=req.sig, msg=hreq, gpk=gpk):
        return JSONResponse(
            content={"message": "Invalid Signature"}, 
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    mylogging.mylogger.debug(f"{config.KEY_ROTATION_LABEL}:{os.getpid()} --> Received request to evaluate with index {req.i_k}")
    keypairs = oprf.KeyRotation.get_keys(req.i_k)
    
    evals = oprf.evaluate(keypairs, req.x)
    hres = oprf.Utils.to_base64(oprf.Utils.hash256(bytes(misc.stringify(evals), 'utf-8')))
    content = {
        "evals": evals, 
        "sig_r": audit_logging.ecdsa_sign(private_key=isk, data=hreq+hres)
    }

    cache.enqueue_log({
        "type": config.LOG_TYPE_CID_GEN,
        "x": req.x,
        "i_k": req.i_k,
        "tk": req.bt,
        "peers": req.peers,
        "hres": oprf.Utils.to_base64(oprf.Utils.hash256(bytes(misc.stringify(content), 'utf-8'))),
        "sig": req.sig,
    })

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