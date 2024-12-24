import json
from redis import Redis
from cpex.config import CACHE_HOST, CACHE_PORT, CACHE_PASS, CACHE_DB, NODE_ID, get_container_prefix

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
    if type(value) == dict or type(value) == list:
        value = json.dumps(value)
    if type(value) != str:
        raise TypeError("Value must be a string")
    return connect().setex(key, seconds, value)

def get_other_repositories(mode: str):
    all_repos = get_all_repositories(mode=mode)
    return [repo for repo in all_repos if repo.get('id') != NODE_ID]

def get_all_repositories(mode: str):
    repos = find('repositories', dict)
    return [repo for repo in repos if repo.get('name', '').startswith(get_container_prefix(mode))]
