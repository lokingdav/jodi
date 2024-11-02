from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import JSONResponse
from typing import Annotated

import cpex.config as config
import cpex.requests.validators.cps_reqs as cps_reqs
import cpex.requests.handlers.cps_handler as cps_handler

import cpex.stirshaken.certs as sti_certs
import cpex.helpers.files as files
import cpex.constants as constants

conf = None
certs_file = config.CONF_DIR + f'/cps.{config.CPS_ID}.certs.json'

def init_server():
    global conf
    
    conf = files.read_json(certs_file)
    
    if not conf:
        cert, (sk, csr) = None, sti_certs.client_keygen(name=f'cps_{config.CPS_ID}')
        
        while not cert:
            try:
                print("********* Requesting certificate *********")
                cert = sti_certs.request_cert(csr)
            except Exception as e:
                print("Could not obtain certificate from the Certificate Repository")
                print(e)
            
        conf = { constants.CERT_KEY: cert, constants.PRIV_KEY: sk }
        
        files.override_json(fileloc=certs_file, data=conf)
        
    return FastAPI()
        

app = init_server()

@app.post("/publish")
async def publish(req: cps_reqs.PublishFormReq):
    if not PublishRequest.validate_request(orig=orig, dest=dest, req=req, auth_token=authorization):
        raise HTTPException(
            status_code=400, 
            detail={"error": "Invalid request"}
        )
    
    return JSONResponse(
        content={"message": "OK"}, 
        status_code=status.HTTP_201_CREATED
    )

@app.post("/republish")
async def republish(req: cps_reqs.RepublishFormReq):
    return req.model_dump()

@app.post("/retrieve")
async def republish(req: cps_reqs.RetrieveFormReq):
    return req.model_dump()

@app.get("/health")
async def health():
    return {"cps_id": config.CPS_ID, "message": "OK", "status": 200}