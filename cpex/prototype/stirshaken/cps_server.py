from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse

import cpex.config as config
from cpex.requests.validators.cps_reqs import PublishRequest, RepublishRequest, RetrieveRequest

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
                print("Could not obtain certificate from the Certificate Repository.")
                print(e)
            
        conf = { constants.CERT_KEY: cert, constants.PRIV_KEY: sk }
        
        files.override_json(fileloc=certs_file, data=conf)
        
    return FastAPI()
        

app = init_server()

@app.post("/publish")
async def publish(req: PublishRequest):
    return JSONResponse(
        content={"message": "OK"}, 
        status_code=status.HTTP_201_CREATED
    )

@app.post("/republish")
async def republish(req: RepublishRequest):
    return req.model_dump()

@app.post("/retrieve")
async def republish(req: RetrieveRequest):
    return req.model_dump()

@app.get("/health")
async def health():
    return {
        "cps_id": config.CPS_ID, 
        "mode": config.CPS_MODE,
        "message": "OK", 
        "status": 200
    }