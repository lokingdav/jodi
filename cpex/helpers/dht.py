import heapq
from cpex.models import cache
from cpex import config
from typing import List
from pylibcpex import Oprf, Utils, Ciphering

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

def get_stores(keys, count: int, nodes: List[dict] = None):
    stores = nodes if nodes else cache.find(key=config.STORES_KEY, dtype=dict)

    if type(keys) == bytes:
        return get_nodes(stores, keys, count)
    
    data = []
    node_count = config.STORES_PER_MULTI_CID if len(keys) > 1 else count
    
    for key in keys:
        data.append(get_nodes(stores, key, node_count))

    return data

def get_evals(keys, count: int, nodes: List[dict] = None):
    evals = nodes if nodes else cache.find(key=config.EVALS_KEY, dtype=dict)

    if type(keys) == bytes:
        return get_nodes(evals, keys, count)
    
    data = []
    for key in keys:
        data.append(get_nodes(evals, key, count))

    return data