from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

import cpex.config as config
from cpex.crypto import groupsig, oprf

kr_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    kr_instance = oprf.begin_key_rotation()
    yield
    kr_instance.stop_rotation()

app = FastAPI(lifespan=lifespan)

class EvaluateRequest(BaseModel):
    x: str
    idx: int
    sig: str
    
@app.post("/evaluate")
async def evaluate(req: EvaluateRequest):
    msg = str(req.idx) + str(req.x)
    if not groupsig.verify(req.sig, msg, config.TGS_GPK):
        return JSONResponse(
            content={"message": "Invalid Signature"}, 
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    privk, publk = kr_instance.get_key(req.idx)
    
    return JSONResponse(
        content=oprf.evaluate(privk=privk, publk=publk, x=req.x), 
        status_code=status.HTTP_201_CREATED
    )

@app.get("/health")
async def health():
    return { "message": "OK", "status": 200 }