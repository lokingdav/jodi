from pylibjodi import Voprf, Utils, Ciphering
import jodi.config as config
from jodi.crypto import groupsig, billing, audit_logging
from jodi.helpers import dht, misc
from typing import List
import re, time, traceback
from datetime import datetime
from itertools import product

def get_peers(nodes):
    return ".".join([node.get('id') for node in nodes])

def normalize_ts() -> str:
    return datetime.now().date()

def normalize_tn(tn: str): 
    tn = re.sub(r"[^\d]", "", tn)
    return f"+{tn}"
    
def normalize_call_details(src: str, dst: str):
    return f'{normalize_tn(src)}.{normalize_tn(dst)}.{normalize_ts()}'

def get_index_from_call_details(call_details: str) -> int:
    digest: bytes = Utils.hash160(call_details.encode('utf-8'))
    return int(digest.hex(), 16) % config.KEYLIST_SIZE

def create_evaluation_requests(call_details: str, n_ev: int, gsk, gpk, bt) -> bytes:
    i_k: int = get_index_from_call_details(call_details)

    calldt_hash = Utils.hash256(bytes(call_details, 'utf-8'))
    evaluators = dht.get_evals(
        keys=calldt_hash, 
        count=n_ev,
    )

    # Blind and sign the call details
    x, mask = Voprf.blind(call_details)
    x_str = Utils.to_base64(x)
    peers = get_peers(evaluators)

    hreq = Utils.to_base64(Utils.hash256(bytes(x_str + str(i_k) + bt + peers, 'utf-8')))

    sig = groupsig.sign(msg=hreq, gsk=gsk, gpk=gpk)
    
    # Create evaluation requests
    requests = []
    for ev in evaluators:
        requests.append({
            'nodeId': ev.get('id'),
            'avail': ev.get('avail', None),
            'url': ev.get('url') + '/evaluate', 
            'data': { 'i_k': i_k, 'x': x_str, 'sig': sig, 'bt': bt, 'peers': peers}
        })
    
    return requests, mask, hreq

def create_call_ids(responses: List[dict], mask: bytes, req_type: str, call_details: str) -> bytes:
    cidsets, xor, edge_case, X = [], bytes(0), False, None
    
    for res in responses:
        cid_1 = Voprf.unblind(Utils.from_base64(res[0]['fx']), mask)
        
        if Voprf.verify(Utils.from_base64(res[0]['vk']), call_details, cid_1):
            xor = Utils.xor(xor, cid_1)
            X = [cid_1]
            
        if req_type == 'retrieve' and len(res) == 2:
            cid_2 = Voprf.unblind(Utils.from_base64(res[1]['fx']), mask)
            
            if Voprf.verify(Utils.from_base64(res[1]['vk']), call_details, cid_2):
                X = [cid_1, cid_2]
                edge_case = True
                
        if X:
            cidsets.append(X)

    answers = []
    
    if req_type == 'publish' or edge_case == False:
        answers = [xor]
    else:
        cidsets = list(product(*cidsets))
        for cidlist in cidsets:
            xor = bytes(0)
            for cid in cidlist:
                xor = Utils.xor(xor, cid)
            answers.append(xor)
            
    # print({
    #     'edge_case': edge_case,
    #     'req_type': req_type,
    #     'call_details': call_details,
    #     'xor': xor.hex(),
    #     'answers': [ans.hex() for ans in answers]
    # })
        
    return [Utils.hash256(answer) for answer in answers]

def create_storage_requests(call_id: bytes, msg: str, n_ms: int, gsk, gpk, bt, stores = None) -> List[dict]:
    stores = dht.get_stores(keys=call_id, count=n_ms, nodes=stores)

    # Generate the index, encrypt msg and sign request
    idx = Utils.to_base64(Utils.hash256(call_id))
    ctx = encrypt_and_mac(call_id=call_id, plaintext=msg)
    peers = get_peers(stores)

    pp = Utils.to_base64(Utils.hash256(bytes(idx + ctx, 'utf-8')))
    bb = billing.get_billing_hash(bt, peers)
    sig = groupsig.sign(msg=pp + bb, gsk=gsk, gpk=gpk)
    
    # Create storage requests for closest n_ms stores
    requests = []
    for store in stores:
        requests.append({
            'nodeId': store['id'],
            'avail': store.get('avail', None),
            'url': store['url'] + '/publish',
            'data': {'idx': idx, 'ctx': ctx, 'sig': sig, 'bt': bt, 'peers': peers}
        })

    return requests

def create_retrieve_requests(call_ids: List[bytes], n_ms: int, gsk, gpk, bt) -> List[dict]:
    requests = []
    stores_per_cid = dht.get_stores(keys=call_ids, count=n_ms)

    assert len(call_ids) == len(stores_per_cid)

    for i, stores in enumerate(stores_per_cid):
        idx = Utils.to_base64(Utils.hash256(call_ids[i]))
        peers = get_peers(stores)

        pp = Utils.to_base64(Utils.hash256(bytes(idx, 'utf-8')))
        bb = billing.get_billing_hash(bt, peers)

        sig = groupsig.sign(msg=pp + bb, gsk=gsk, gpk=gpk)

        for store in stores:
            requests.append({
                'nodeId': store['id'],
                'avail': store.get('avail', None),
                'url': store['url'] + '/retrieve',
                'data': { 'idx': idx, 'sig': sig, 'bt': bt, 'peers': peers }
            })

    return requests

def encrypt_and_mac(call_id: bytes, plaintext: str) -> str:
    c_0 = Utils.random_bytes(32)
    kenc = Utils.hash256(Utils.xor(c_0, call_id))
    c_1 = Ciphering.enc(kenc, plaintext.encode('utf-8'))
    return Utils.to_base64(c_0) + ':' + Utils.to_base64(c_1)

def decrypt(call_ids: List[bytes], responses: List[dict], gpk, ipk):
    if not (call_ids and responses):
        return None
    
    call_ids = { Utils.to_base64(Utils.hash256(cid)): cid for cid in call_ids }
    
    for res_entry in responses:
        if '_error' in res_entry or 'sig_r' not in res_entry:
            continue
        
        res = res_entry['res']
        
        hreq = billing.Utils.to_base64(billing.Utils.hash256(bytes(res['idx'], 'utf-8')))
        hres = billing.Utils.to_base64(billing.Utils.hash256(bytes(misc.stringify(res), 'utf-8')))
        
        if not audit_logging.ecdsa_verify(public_key=ipk, data=hreq+hres, sigma=res_entry['sig_r']):
            continue
        
        pp = Utils.to_base64(Utils.hash256(bytes(res['idx'] + res['ctx'], 'utf-8')))
        if '_error' in res or not groupsig.verify(sig=res['sig'], msg=pp + res['bb'], gpk=gpk):
            continue
        
        try:
            c_0, c_1 = res['ctx'].split(':')
            kenc = Utils.hash256(Utils.xor(Utils.from_base64(c_0), call_ids[res['idx']]))
            msg: bytes = Ciphering.dec(kenc, Utils.from_base64(c_1))
            
            if msg:
                return msg.decode('utf-8')
        except:
            traceback.print_exc()
            pass
        
    return None