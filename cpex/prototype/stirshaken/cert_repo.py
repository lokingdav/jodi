from fastapi import FastAPI, HTTPException
from cpex.models import persistence
from cpex.prototype.stirshaken import stirsetup
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    stirsetup.setup()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/certs/{key}")
async def get_certificate(key: str):
    cert = persistence.get_cert(key=key)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert

@app.get("/health")
async def check_health():
    """
    Health check endpoint to verify that the service is running.
    """
    return {"message": "OK", "status": 200}
