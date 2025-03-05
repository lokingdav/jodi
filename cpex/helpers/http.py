from typing import List, Dict
import aiohttp
import asyncio

def get_headers(headers: dict = {}) -> dict:
    return {
        'Content-Type': 'application/json',
        **headers
    }

async def post(session: aiohttp.ClientSession, url: str, data: dict, headers: dict = {}) -> dict:
    try:
        async with session.post(url, json=data, headers=get_headers(headers)) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        return {"_error": str(e)}

async def posts(reqs: List[dict]) -> List[dict]:
    async with aiohttp.ClientSession() as session:
        tasks = [ post(session, req['url'], req['data'], req.get('headers', {})) for req in reqs ]
        return await asyncio.gather(*tasks)
    
async def posts_race(reqs: List[Dict]) -> Dict:
    async with aiohttp.ClientSession() as session:
        tasks = {asyncio.create_task(post(session, req["url"], req["data"], req.get("headers", {}))): req for req in reqs}
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
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=get_headers(headers)) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            return {"_error": str(e)}
