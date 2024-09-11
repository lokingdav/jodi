from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import JSONResponse
import oobshaken.config as config
from typing import Annotated
from oobshaken.schema import Publish as PubForm, Republish
from oobshaken.cps import Publish as PublishRequest

app = FastAPI()

if config.is_atis(): 
    @app.post("/passports/{dest}/{orig}")
    async def publish(orig: str, dest: str, req: PubForm, authorization: Annotated[str | None, Header()] = None):
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
    async def republish(req: Republish):
        return req.model_dump()

    @app.get("/health")
    async def health():
        return {"message": "OK", "status": 200}
else:
    pass