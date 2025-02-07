import json
from redis import Redis
from cpex.config import CACHE_HOST, CACHE_PORT, CACHE_PASS, CACHE_DB, NODE_FQDN, CPS_KEY

client = None

def set_client(cclient: Redis = None):
    global client
    client = cclient

def connect():
    return Redis(
        host=CACHE_HOST,
        port=CACHE_PORT,
        password=CACHE_PASS,
        db=CACHE_DB,
        decode_responses=True
    )

def find(key: str, dtype = str):
    data = client.get(key) or None

    if data and dtype == int:
        return int(data)
    
    if data and dtype == dict:
        return json.loads(data)
    
    return data

def save(key: str, value: str):
    if type(value) != str:
        raise TypeError("Value must be a string")
    
    return client.set(key, value)

def cache_for_seconds(key: str, value: str, seconds: int):
    if type(value) == dict or type(value) == list:
        value = json.dumps(value)
    if type(value) != str:
        raise TypeError("Value must be a string")
    return client.setex(key, seconds, value)

def get_other_cpses():
    repos = find(key=CPS_KEY, dtype=dict)
    return [repo for repo in repos if repo.get('fqdn') != NODE_FQDN]
