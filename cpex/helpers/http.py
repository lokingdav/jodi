from typing import List, Dict
import aiohttp
import asyncio

keep_alive_session: aiohttp.ClientSession = None

def create_session(event_loop=None, limit=100, keepalive_timeout=60) -> aiohttp.ClientSession:
    connector = aiohttp.TCPConnector(loop=event_loop, limit=limit, keepalive_timeout=keepalive_timeout)
    return aiohttp.ClientSession(loop=event_loop, connector=connector)
        
def set_session(session: aiohttp.ClientSession):
    global keep_alive_session
    keep_alive_session = session
    
def destroy_session():
    global keep_alive_session
    loop = asyncio.get_event_loop()
    if keep_alive_session:
        loop.run_until_complete(keep_alive_session.close())
        
async def async_destroy_session():
    global keep_alive_session
    if keep_alive_session:
        await keep_alive_session.close()

def get_headers(headers: dict = {}) -> dict:
    return {
        'Content-Type': 'application/json',
        **headers
    }

async def post(url: str, data: dict, headers: dict = {}) -> dict:
    try:
        async with keep_alive_session.post(url, json=data, headers=get_headers(headers)) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        return {"_error": str(e)}

async def posts(reqs: List[dict]) -> List[dict]:
    tasks = [ post(url=req['url'], data=req['data'], headers=req.get('headers', {})) for req in reqs ]
    return await asyncio.gather(*tasks)
    
async def posts_race(reqs: List[Dict]) -> Dict:
    tasks = {asyncio.create_task(post(url=req["url"], data=req["data"], headers=req.get("headers", {}))): req for req in reqs}
    failures = []
    while tasks:
        done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            result = await task
            if "_error" not in result:
                for p in pending:
                    p.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                return [result]
            else:
                failures.append(result)
        
        for task in done:
            tasks.pop(task, None)

    return failures

async def get(url: str, params: dict = {}, headers: dict = {}) -> dict:
    try:
        async with keep_alive_session.get(url, params=params, headers=get_headers(headers)) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        return {"_error": str(e)}
