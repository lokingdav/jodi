from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from cpex.crypto import groupsig, oprf

kr_instance = None
gpk = groupsig.get_gpk()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global kr_instance
    kr_instance = oprf.begin_key_rotation()
    yield
    kr_instance.stop_rotation()

app = FastAPI(lifespan=lifespan)

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
    
    print(f"\nReceived request to evaluate {req.x} with index {req.i_k}", flush=True)
    privk, publk = kr_instance.get_key(req.i_k)
    print(f"Using key with index {req.i_k}, \n\tsk: {oprf.Utils.to_base64(privk)}, \n\tpk: {oprf.Utils.to_base64(publk)}", flush=True)
    
    return JSONResponse(
        content=oprf.evaluate(privk=privk, publk=publk, x=req.x), 
        status_code=status.HTTP_201_CREATED
    )

@app.get("/health")
async def health():
    return { 
        "Status": 200,
        "Message": "OK", 
        "Type": "Evaluator", 
    }