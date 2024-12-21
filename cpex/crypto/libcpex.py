from typing import Tuple
from pylibcpex import Oprf, Utils, Ciphering
import cpex.config as config
import cpex.constants as constants
from cpex.crypto import groupsig
from cpex.helpers import http
from cpex.models import cache
from typing import List
import jwt, time

def normalizeTs(timestamp: int) -> int:
    seconds_in_minute = 60
    return timestamp - (timestamp % seconds_in_minute)

def get_call_details(src: str, dst: str):
    ts = normalizeTs(int(time.time()))
    return src + dst + str(ts)

def get_index_from_call_details(call_details: str) -> int:
    return int(call_details.encode().hex(), 16) % config.OPRF_KEYLIST_SIZE

async def generate_call_id(call_details: str) -> bytes:
    idx: int = get_index_from_call_details(call_details)

    x0, r0 = Oprf.blind(call_details)
    x1, r1 = Oprf.blind(call_details)
    x0_str, x1_str = Utils.to_base64(x0), Utils.to_base64(x1)
    
    sig0_str = groupsig.sign(msg=str(idx) + x0_str, gsk=config.TGS_GSK, gpk=config.TGS_GPK)
    sig1_str = groupsig.sign(msg=str(idx) + x1_str, gsk=config.TGS_GSK, gpk=config.TGS_GPK)
    reqs = [
        {'url': config.OPRF_SERVER_1_URL + '/evaluate', 'data': { 'idx': idx, 'x': x0_str, 'sig': sig0_str}},
        {'url': config.OPRF_SERVER_2_URL + '/evaluate', 'data': { 'idx': idx, 'x': x1_str, 'sig': sig1_str}},
    ]

    res = await http.posts(reqs=reqs)
    L0: bytes = Oprf.unblind(Utils.from_base64(res[0]['fx']), Utils.from_base64(res[0]['vk']), r0)
    L1: bytes = Oprf.unblind(Utils.from_base64(res[1]['fx']), Utils.from_base64(res[1]['vk']), r1)

    return Utils.hash256(Utils.xor(L0, L1))

def find_node(nodes: List[dict], key: bytes) -> dict:
    closest_node = None
    closest_dist = float('inf')
    closest_dist_index = -1

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
            closest_dist_index = i
            
    return closest_node, closest_dist_index

def create_publish_requests(call_id: bytes, ctx: bytes, nodes: List[dict], count: int) -> List[dict]:
    if not nodes: raise Exception('No message store available')

    call_id, ctx, reqs = Utils.to_base64(call_id), Utils.to_base64(ctx), []

    for i in range(1, count + 1):
        idx: bytes = Utils.hash256(bytes(call_id + str(i), 'utf-8'))
        node, index = find_node(nodes=nodes, key=idx)
        idx = Utils.to_base64(idx)
        reqs.append({
            'url': node['url'] + '/publish',
            'data': { 
                'idx': idx, 
                'ctx': ctx, 
                'sig': groupsig.sign(msg=idx + ctx, gsk=config.TGS_GSK, gpk=config.TGS_GPK) 
            }
        })
        nodes.pop(index)

    return reqs

def create_retrieve_requests(call_id: bytes, nodes: List[dict], count: int) -> List[dict]:
    if not nodes: raise Exception('No message store available')

    call_id, reqs = Utils.to_base64(call_id), []

    for i in range(1, count + 1):
        idx: bytes = Utils.hash256(bytes(call_id + str(i), 'utf-8'))
        node, index = find_node(nodes=nodes, key=idx)
        idx = Utils.to_base64(idx)
        reqs.append({
            'url': node['url'] + '/retrieve',
            'data': { 
                'idx': idx, 
                'sig': groupsig.sign(msg=idx, gsk=config.TGS_GSK, gpk=config.TGS_GPK) 
            }
        })
        nodes.pop(index)

    return reqs

def encrypt_and_mac(call_id: bytes, plaintext: str):
    return Ciphering.enc(call_id, plaintext.encode())

def decrypt(call_id: bytes, responses: List[dict], src: str, dst: str):
    src, dst, tokens = str(src), str(dst), []
    
    for res in responses:
        if not groupsig.verify(sig=res['sig'], msg=res['idx'] + res['ctx'], gpk=config.TGS_GPK):
            continue
        tokens.append(Ciphering.dec(call_id, Utils.from_base64(res['ctx'])))

    return list(set(tokens))