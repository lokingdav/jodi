import random
from cpex.helpers import misc

def normalizeTs(ts: int):
    return ts

def get_label(src: str, dst: str, ts: int):
    return misc.hash256(f'{src}||{dst}|{ts}')

def secure(label: str, passport: str, gsp: dict):
    data = {
        'idx': misc.hash256(random.randint(1, 9999)),
        'ctx': passport, # Will be encrypted later,
        'exp': None, # To be changed
        'sig': misc.hash256(random.randint(1, 9999))
    }
    shares = [(label, 's1'), (label, 's2'), (label, 's3')]
    return data, shares

def get_publish_requests(cps_url: str, cpc_urls: list[str], data: dict, shares: list):
    reqs = [(cps_url, data['data'], None)]