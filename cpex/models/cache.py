import json
from redis import Redis
from cpex.config import CACHE_HOST, CACHE_PORT, CACHE_PASS, CACHE_DB, NODE_ID, get_container_prefix, CPS_KEY

def connect():
    return Redis(
        host=CACHE_HOST,
        port=CACHE_PORT,
        password=CACHE_PASS,
        db=CACHE_DB,
        decode_responses=True
    )

def find(client: Redis, key: str, dtype = str):
    data = client.get(key) or None

    if data and dtype == int:
        return int(data)
    
    if data and dtype == dict:
        return json.loads(data)
    
    return data

def save(client: Redis, key: str, value: str):
    if type(value) != str:
        raise TypeError("Value must be a string")
    
    return client.set(key, value)

def cache_for_seconds(client: Redis, key: str, value: str, seconds: int):
    if type(value) == dict or type(value) == list:
        value = json.dumps(value)
    if type(value) != str:
        raise TypeError("Value must be a string")
    return client.setex(key, seconds, value)

def get_other_cpses():
    repos = find(CPS_KEY, dict)
    return [repo for repo in repos if repo.get('id') != NODE_ID]
