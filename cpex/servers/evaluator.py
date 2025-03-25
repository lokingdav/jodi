import os, time
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cpex.crypto import groupsig, oprf, billing
from cpex.models import cache
from cpex.helpers import mylogging
from cpex import config

mylogging.init_mylogger('evaluator', 'logs/evaluator.log')
cache.set_client(cache.connect())
gpk = groupsig.get_gpk()

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
    
    pp = oprf.Utils.to_base64(oprf.Utils.hash256(bytes(str(req.i_k) + req.x, 'utf-8')))
    bb = billing.get_billing_hash(req.bt, req.peers)

    if not groupsig.verify(sig=req.sig, msg=pp + bb, gpk=gpk):
        return JSONResponse(
            content={"message": "Invalid Signature"}, 
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # mylogging.mylogger.debug(f"{config.KEY_ROTATION_LABEL}:{os.getpid()} --> Received request to evaluate {req.x} with index {req.i_k}")
    keypairs = oprf.KeyRotation.get_keys(req.i_k)
    # mylogging.mylogger.debug(f"{config.KEY_ROTATION_LABEL}:{os.getpid()} --> Using key with index {req.i_k}, keypairs: {keypairs}")
    
    content = oprf.evaluate(keypairs, req.x)
    # mylogging.mylogger.debug(f"{config.KEY_ROTATION_LABEL}:{os.getpid()} --> Evaluated {req.x} with index {req.i_k} in {round((time.perf_counter() - start_time)*1000, 2)} ms")

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