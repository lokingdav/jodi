import os
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cpex.crypto import groupsig, oprf
from cpex.models import cache
from cpex.helpers import mylogging

mylogging.init_mylogger('evaluator', 'evaluator.log')
cache.set_client(cache.connect())
gpk = groupsig.get_gpk()

app = FastAPI()

class EvaluateRequest(BaseModel):
    i_k: int
    x: str
    sig: str
    
@app.post("/evaluate")
async def evaluate(req: EvaluateRequest):
    if not groupsig.verify(sig=req.sig, msg=str(req.i_k) + str(req.x), gpk=gpk):
        return JSONResponse(
            content={"message": "Invalid Signature"}, 
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # mylogging.mylogger.debug(f"\n{os.getpid()} --> Received request to evaluate {req.x} with index {req.i_k}")
    sk, pk = oprf.KeyRotation.get_key(req.i_k)
    # mylogging.mylogger.debug(f"{os.getpid()} --> Using key with index {req.i_k}, \n\tsk: {oprf.Utils.to_base64(sk)}\n\tpk: {oprf.Utils.to_base64(pk)}")
    
    return JSONResponse(
        content=oprf.evaluate(sk=sk, pk=pk, x=req.x), 
        status_code=status.HTTP_201_CREATED
    )

@app.get("/health")
async def health():
    return { 
        "Status": 200,
        "Message": "OK", 
        "Type": "Evaluator", 
    }