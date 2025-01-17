import heapq
from cpex.models import cache
from cpex import config
from typing import List
from pylibcpex import Oprf, Utils, Ciphering

cache_client = None

def set_cache_client(client):
    global cache_client
    cache_client = client

def get_nodes(nodes: List[dict], key: bytes, count: int) -> dict:
    if not isinstance(key, bytes) or len(key) == 0:
        raise ValueError('Key must be a non-empty bytes object')
    if len(key) != 32:
        raise ValueError('Key must be a 32-byte object')
        
    heap = []
    
    for node in nodes:
        xor = Utils.xor(bytes.fromhex(node['id']), key)
        distance = int.from_bytes(xor, byteorder='big')
        heapq.heappush(heap, (distance, node))
    return [heapq.heappop(heap)[1] for _ in range(min(count, len(heap)))]

def get_stores(key: bytes, count: int, nodes: List[dict] = None):
    stores = nodes if nodes else cache.find(client=cache_client, key=config.STORES_KEY, dtype=dict)
    return get_nodes(stores, key, count)
    
def get_evals(key: bytes, count: int, nodes: List[dict] = None):
    evals = nodes if nodes else cache.find(client=cache_client, key=config.EVALS_KEY, dtype=dict)
    return get_nodes(evals, key, count)