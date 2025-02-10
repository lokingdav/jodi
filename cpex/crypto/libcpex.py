from pylibcpex import Oprf, Utils, Ciphering
import cpex.config as config
from cpex.crypto import groupsig
from cpex.helpers import dht
from typing import List
import re
from datetime import datetime

def normalize_ts() -> str:
    return datetime.now().date()

def normalize_tn(tn: str): 
    tn = re.sub(r"[^\d]", "", tn)
    return f"+{tn}"
    
def normalize_call_details(src: str, dst: str):
    return f'{normalize_tn(src)}.{normalize_tn(dst)}.{normalize_ts()}'

def get_index_from_call_details(call_details: str) -> int:
    digest: bytes = Utils.hash160(call_details.encode('utf-8'))
    return int(digest.hex(), 16) % config.OPRF_KEYLIST_SIZE

def create_evaluation_requests(call_details: str, n_ev: int, gsk, gpk) -> bytes:
    i_k: int = get_index_from_call_details(call_details)
    calldt_hash = Utils.hash256(bytes(call_details, 'utf-8'))
    evaluators = dht.get_evals(
        key=calldt_hash, 
        count=n_ev,
    )

    # Blind and sign the call details
    x, mask = Oprf.blind(call_details)
    x_str = Utils.to_base64(x)
    sig = groupsig.sign(msg=str(i_k) + x_str, gsk=gsk, gpk=gpk)
    
    # Create evaluation requests
    requests = []
    for ev in evaluators:
        requests.append({
            'nodeId': ev.get('id'),
            'avail': ev.get('avail', None),
            'url': ev.get('url') + '/evaluate', 
            'data': { 'i_k': i_k, 'x': x_str, 'sig': sig}
        })
    
    return requests, mask

def create_call_id(responses: List[dict], mask: bytes) -> bytes:
    xor = None
    
    for i in range(len(responses)):
        if '_error' in responses[i]:
            continue
        
        cid_i = Oprf.unblind(
            Utils.from_base64(responses[i]['fx']), 
            Utils.from_base64(responses[i]['vk']), 
            mask
        )
        
        if xor is None:
            xor = cid_i
        else:
            xor = Utils.xor(xor, cid_i)
        
    return Utils.hash256(xor) if xor else None

def create_storage_requests(call_id: bytes, msg: str, n_ms: int, gsk, gpk, stores = None) -> List[dict]:
    # Generate the index, encrypt msg and sign request
    idx = Utils.to_base64(Utils.hash256(call_id))
    ctx = encrypt_and_mac(call_id=call_id, plaintext=msg)
    sig = groupsig.sign(msg=idx + ctx, gsk=gsk, gpk=gpk)
    
    # Create storage requests for closest n_ms stores
    requests = []
    stores = dht.get_stores(key=call_id, count=n_ms, nodes=stores)
    for store in stores:
        requests.append({
            'nodeId': store['id'],
            'avail': store.get('avail', None),
            'url': store['url'] + '/publish',
            'data': {'idx': idx, 'ctx': ctx, 'sig': sig }
        })

    return requests

def create_retrieve_requests(call_id: bytes, n_ms: int, gsk, gpk, stores=None) -> List[dict]:
    # Generate the index and sign request
    idx = Utils.to_base64(Utils.hash256(call_id))
    sig = groupsig.sign(msg=idx, gsk=gsk, gpk=gpk)

    requests = []
    stores = dht.get_stores(key=call_id, count=n_ms, nodes=stores)
    for store in stores:
        requests.append({
            'nodeId': store['id'],
            'avail': store.get('avail', None),
            'url': store['url'] + '/retrieve',
            'data': { 'idx': idx, 'sig': sig }
        })

    return requests

def encrypt_and_mac(call_id: bytes, plaintext: str) -> str:
    c_0 = Utils.random_bytes(32)
    kenc = Utils.hash256(Utils.xor(c_0, call_id))
    c_1 = Ciphering.enc(kenc, plaintext.encode('utf-8'))
    return Utils.to_base64(c_0) + ':' + Utils.to_base64(c_1)

def decrypt(call_id: bytes, responses: List[dict], src: str, dst: str, gpk):
    if not (call_id and responses):
        return None
    
    for res in responses:
        if '_error' in res or not groupsig.verify(sig=res['sig'], msg=res['idx'] + res['ctx'], gpk=gpk):
            continue
        try:
            c_0, c_1 = res['ctx'].split(':')
            kenc = Utils.hash256(Utils.xor(Utils.from_base64(c_0), call_id))
            msg: bytes = Ciphering.dec(kenc, Utils.from_base64(c_1))
            
            if msg:
                return msg.decode('utf-8')
        except:
            continue
        
    return None