import json, redis, datetime
from jodi.config import CACHE_HOST, CACHE_PORT, CACHE_PASS, CACHE_DB, NODE_FQDN, LOG_BATCH_KEY

client = None

def set_client(cclient: redis.Redis = None):
    global client
    client = cclient

def connect(decode_responses: bool = True):
    return redis.Redis(
        host=CACHE_HOST,
        port=CACHE_PORT,
        password=CACHE_PASS,
        db=CACHE_DB,
        decode_responses=decode_responses
    )

def find(key: str, dtype = str):
    data = client.get(key) or None

    if data and dtype == int:
        return int(data)
    
    if data and dtype == dict:
        return json.loads(data)
    
    return data

def find_all(keys: list, dtype = str):
    data = client.mget(keys)
    if dtype == int:
        return [int(d) for d in data if d]
    if dtype == dict:
        return [json.loads(d) for d in data if d]
    
    return data

def save(key: str, value: str):
    if type(value) != str:
        raise TypeError("Value must be a string")
    return client.set(key, value)

def save_all(data: dict):
    return client.mset(data)

def cache_for_seconds(key: str, value: str, seconds: int):
    if type(value) == dict or type(value) == list:
        value = json.dumps(value)
    if type(value) != str:
        raise TypeError("Value must be a string")
    return client.setex(key, seconds, value)

def get_other_cpses(key):
    # print("Finding other CPSes except", key, flush=True)
    repos = find(key=key, dtype=dict)
    # print("Found other CPSes", repos, flush=True)
    if not repos:
        return []
    return [repo for repo in repos if repo.get('fqdn') != NODE_FQDN]

def save_certificates(certificates: dict):
    for key, cred in certificates.items():
        save(key=key, value=cred['cert'])
        
        
def enqueue_log(entry:dict):
    entry['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.lpush(LOG_BATCH_KEY, json.dumps(entry))
