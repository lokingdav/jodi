from fastapi import FastAPI

app = FastAPI()

@app.get("/certs/{spc}")
async def get_certificate(spc: str):
    spc = spc.split('.')
    if (len(spc) != 2) or (spc[1] != 'cert' and spc[1] not in [f'sp{_}' for _ in range(1, 10)]):
        return {'error': 'Invalid SPC'}
    path, key = f'certs/{spc[0]}/cert.pem', None
    with open(path, 'rb') as f:
            key = f.read()
    return key

@app.get("/health")
async def check_health():
    return {"message": "OK", "status": 200}