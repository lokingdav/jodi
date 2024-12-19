import json
from redis import Redis
from cpex.config import CACHE_HOST, CACHE_PORT, CACHE_PASS, CACHE_DB

def connect():
    return Redis(
        host=CACHE_HOST,
        port=CACHE_PORT,
        password=CACHE_PASS,
        db=CACHE_DB,
        decode_responses=True
    )

def find(key: str, dtype = str):
    data = connect().get(key) or None

    if data and dtype == int:
        return int(data)
    
    if data and dtype == dict:
        return json.loads(data)
    
    return data

def save(key: str, value: str):
    if type(value) != str:
        raise TypeError("Value must be a string")
    
    return connect().set(key, value)

def cache_for_seconds(key: str, value: str, seconds: int):
    if type(value) != str:
        raise TypeError("Value must be a string")
    return connect().setex(key, seconds, value)