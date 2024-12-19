from typing import Tuple
from pylibcpex import Oprf, Utils, Ciphering
import cpex.config as config, constants
from cpex.crypto import groupsig
from cpex.helpers import http
from cpex.models import cache
from typing import List
import jwt
from datetime import datetime

def normalizeTs(timestamp: int) -> int:
    seconds_in_minute = 60
    return timestamp - (timestamp % seconds_in_minute)

def get_call_details(src: str, dst: str):
    ts = normalizeTs(int(datetime.timestamp()))
    return src + dst + str(ts)

def generate_call_id(call_details: str) -> bytes:
    x0, r0 = Oprf.blind(bytes(call_details))
    x1, r1 = Oprf.blind(bytes(call_details))
    x0_str, x1_str = Utils.to_base64(x0), Utils.to_base64(x1)
    
    sig1_str = groupsig.sign(msg=x0_str, gsk=config.GS_GSK, gpk=config.GS_GPK)
    sig2_str = groupsig.sign(msg=x1_str, gsk=config.GS_GSK, gpk=config.GS_GPK)
    reqs = [
        {'url': config.OPRF_SERVER_1_URL + '/evaluate', 'data': {'x': x0_str, 'sig': sig1_str}},
        {'url': config.OPRF_SERVER_2_URL + '/evaluate', 'data': {'x': x1_str, 'sig': sig2_str}},
    ]

    res = http.posts(reqs=reqs)
    L0: bytes = Oprf.unblind(res[0]['fx'], res[0]['vk'], r0)
    L1: bytes = Oprf.unblind(res[1]['fx'], res[1]['vk'], r1)

    return Utils.hash256(Utils.xor(L0, L1))

def find_node(nodes, key: bytes) -> dict:
    closest_node = None
    closest_dist = float('inf')

    for i in range(len(nodes)):
        distance = int.from_bytes(
            Utils.xor(
                bytes.fromhex(nodes[i]['id']), # hex of hash160
                Utils.hash160(key) # hash key to 160 bits
            ), 
            byteorder='big'
        )
        if distance < closest_dist:
            closest_dist, closest_node = distance, nodes[i]

    return closest_node

def create_publish_requests(count: int, call_id: bytes, ctx: bytes) -> List[dict]:
    nodes = cache.find(constants.MESSAGE_STORES_KEY)
    if not nodes: raise Exception('No message store available')

    call_id, ctx, reqs = Utils.to_base64(call_id), Utils.to_base64(ctx), []

    for i in range(1, count + 1):
        idx: bytes = Utils.hash256(call_id + str(i))
        node: dict = find_node(nodes=nodes, key=idx)
        reqs.append({
            'url': node['url'] + '/publish',
            'data': { 
                'idx': idx, 
                'ctx': ctx, 
                'sig': groupsig.sign(msg=idx + ctx, gsk=config.GS_GSK, gpk=config.GS_GPK) 
            }
        })

    return reqs

def create_retrieve_requests(count: int, call_id: bytes) -> List[dict]:
    nodes = cache.find(constants.MESSAGE_STORES_KEY)
    if not nodes: raise Exception('No message store available')

    call_id, reqs = Utils.to_base64(call_id), []

    for i in range(1, count + 1):
        idx: bytes = Utils.hash256(call_id + str(i))
        node: dict = find_node(nodes=nodes, key=idx)
        reqs.append({
            'url': node['url'] + '/retrieve',
            'data': { 
                'idx': idx, 
                'sig': groupsig.sign(msg=idx, gsk=config.GS_GSK, gpk=config.GS_GPK) 
            }
        })

    return reqs

def encrypt_and_mac(call_id: bytes, plaintext: str):
    return Ciphering.enc(call_id, bytes(plaintext))

def decrypt(call_id: bytes, responses: List[dict], src: str, dst: str):
    tokens, ciphertexts = [], []

    for res in responses:
        if not groupsig.verify(sig=res['sig'], msg=res['idx'] + res['ctx'], gpk=config.GS_GPK):
            continue
        ciphertexts.append(res['ctx'])

    ciphertexts = list(set(ciphertexts))

    for ctx in ciphertexts:
        token: str = Ciphering.dec(call_id, Utils.from_base64(ctx))
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, algorithms=[header['alg']])
        if payload['src'] == src and payload['dst'] == dst:
            tokens.append(token)

    return list(set(tokens))