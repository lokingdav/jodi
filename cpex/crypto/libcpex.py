from typing import Tuple
from pylibcpex import Oprf, Utils, Ciphering
import cpex.config as config
import cpex.constants as constants
from cpex.crypto import groupsig
from cpex.helpers import http, dht
from cpex.models import cache
from typing import List
import jwt, time, re


def normalize_ts(timestamp: int) -> int:
    seconds_in_minute = 60
    return timestamp - (timestamp % seconds_in_minute)

def normalize_tn(tn: str): 
    tn = re.sub(r"[^\d]", "", tn)
    return f"+{tn}"
    
def normalize_call_details(src: str, dst: str):
    ts = normalize_ts(int(time.time()))
    return normalize_tn(src) + normalize_tn(dst) + str(ts)

def get_index_from_call_details(call_details: str) -> int:
    digest: bytes = Utils.hash160(call_details.encode('utf-8'))
    return int(digest.hex(), 16) % config.OPRF_KEYLIST_SIZE

def create_evaluation_requests(call_details: str) -> bytes:
    # start = time.perf_counter()
    i_k: int = get_index_from_call_details(call_details)
    # print(f"compute i_k: {(time.perf_counter() - start) * 1000}ms")
    # start = time.perf_counter()
    calldt_hash = Utils.hash256(bytes(call_details, 'utf-8'))
    # print(f"compute calldt_hash: {(time.perf_counter() - start) * 1000}ms")
    # start = time.perf_counter()
    evaluators = dht.get_evals(key=calldt_hash, count=config.OPRF_EV_PARAM)
    # print(f"get_evals: {(time.perf_counter() - start) * 1000}ms")
    # start = time.perf_counter()
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
    # print(f"get gsk, gpk: {(time.perf_counter() - start) * 1000}ms")
    
    masks = []
    requests = []
    start = time.perf_counter()
    for ev in evaluators:
        x, mask = Oprf.blind(call_details)
        masks.append(mask)
        x = Utils.to_base64(x)
        sig: str = groupsig.sign(msg=str(i_k) + x, gsk=gsk, gpk=gpk)
        requests.append({
            'url': ev.get('url') + '/evaluate', 
            'data': { 'i_k': i_k, 'x': x, 'sig': sig}
        })
    # print(f"create requests: {(time.perf_counter() - start) * 1000}ms")
    return requests, masks

def create_call_id(responses: List[dict], masks: List[bytes]) -> bytes:
    xor = None
    for i in range(len(responses)):
        cid_i = Oprf.unblind(
            Utils.from_base64(responses[i]['fx']), 
            Utils.from_base64(responses[i]['vk']), 
            masks[i]
        )
        if xor is None:
            xor = cid_i
        else:
            xor = Utils.xor(xor, cid_i)
        
    return Utils.hash256(xor)

def create_storage_requests(call_id: bytes, msg: str) -> List[dict]:
    stores = dht.get_stores(key=call_id, count=config.REPLICATION)
    call_id_str = Utils.to_base64(call_id)

    requests = []
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
    
    for store in stores:
        idx = Utils.to_base64(Utils.hash256(bytes(call_id_str + store['id'], 'utf-8')))
        ctx = encrypt_and_mac(call_id=call_id, plaintext=msg)
        requests.append({
            'url': store['url'] + '/publish',
            'data': { 
                'idx': idx, 
                'ctx': ctx, 
                'sig': groupsig.sign(msg=idx + ctx, gsk=gsk, gpk=gpk) 
            }
        })

    return requests

def create_retrieve_requests(call_id: bytes) -> List[dict]:
    stores = dht.get_stores(key=call_id, count=config.REPLICATION)
    call_id = Utils.to_base64(call_id)
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
    
    reqs = []

    for store in stores:
        idx = Utils.to_base64(Utils.hash256(bytes(call_id + store['id'], 'utf-8')))
        reqs.append({
            'url': store['url'] + '/retrieve',
            'data': { 
                'idx': idx, 
                'sig': groupsig.sign(msg=idx, gsk=gsk, gpk=gpk) 
            }
        })

    return reqs

def encrypt_and_mac(call_id: bytes, plaintext: str) -> str:
    c_0 = Utils.random_bytes(32)
    kenc = Utils.hash256(Utils.xor(c_0, call_id))
    c_1 = Ciphering.enc(kenc, plaintext.encode('utf-8'))
    return Utils.to_base64(c_0) + ':' + Utils.to_base64(c_1)

def decrypt(call_id: bytes, responses: List[dict], src: str, dst: str):
    src, dst, tokens = str(src), str(dst), []
    gpk = groupsig.get_gpk()
    for res in responses:
        if not groupsig.verify(sig=res['sig'], msg=res['idx'] + res['ctx'], gpk=gpk):
            continue
        c_0, c_1 = res['ctx'].split(':')
        kenc = Utils.hash256(Utils.xor(Utils.from_base64(c_0), call_id))
        msg: bytes = Ciphering.dec(kenc, Utils.from_base64(c_1))
        if msg: return msg.decode('utf-8')
    return None