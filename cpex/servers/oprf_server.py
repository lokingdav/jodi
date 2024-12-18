from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jsonrpc import method, async_dispatch
from jsonrpc.exceptions import InvalidParams

import cpex.config as config

app = FastAPI(title="OPRF JSON-RPC Server", version=config.CPEX_VERSION)


@method
async def evaluate(a: int, b: int) -> int:
    return a + b

@method
async def subtract(a: int, b: int) -> int:
    return a - b

@method
async def multiply(a: int, b: int) -> int:
    return a * b

@method
async def divide(a: int, b: int) -> float:
    if b == 0:
        raise InvalidParams("Division by zero is not allowed")
    return a / b

# JSON-RPC endpoint
@app.post("/")
async def handle_rpc(request: Request):
    # Parse the incoming request
    request_json = await request.json()
    # Dispatch the request to the appropriate JSON-RPC method
    response = await async_dispatch(request_json)
    # Return the JSON-RPC response (already in dict form)
    return JSONResponse(content=response, status_code=200 if "error" not in response else 400)

