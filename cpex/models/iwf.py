import time
import cpex.config as config
from cpex.helpers import misc, http
from typing import List
from cpex.crypto import libcpex, groupsig
from pylibcpex import Utils, Oprf

class CpexIWF:
    def __init__(self, params: dict):
        self.n_ev = params['n_ev']
        self.n_ms = params['n_ms']
        self.gpk = params['gpk']
        self.gsk = params['gsk']
        self.logger = params.get('logger')
        self.fake_proxy = params.get('fake_proxy', False)
        
        # Providers compute time
        self.publish_provider_time = 0
        self.retrieve_provider_time = 0
        
        # Evaluators compute time
        self.publish_ev_time = 0
        self.retrieve_ev_time = 0
        
        # Message stores compute time
        self.publish_ms_time = 0
        self.retrieve_ms_time = 0
    
    async def cpex_publish(self, src, dst, token):
        call_id = await self.cpex_generate_call_id(src=src, dst=dst, req_type='publish')
        
        if not call_id:
            return
        
        reqs = libcpex.create_storage_requests(
            call_id=call_id, 
            msg=token,
            n_ms=self.n_ms,
            gsk=self.gsk,
            gpk=self.gpk
        )
        self.log_msg(f'--> Created Requests for the Following MSs: {[r["nodeId"] for r in reqs]}')
        
        req_time_start = time.perf_counter()
        responses = await self.make_request('publish', requests=reqs)
        req_time_taken = time.perf_counter() - req_time_start
        
        self.publish_provider_time -= req_time_taken # Subtract wait time from compute time
        self.publish_ms_time = req_time_taken / len(reqs) # Average time taken to store a message by a single store
        
        self.log_msg(f'--> Responses: {responses}')
    
    async def cpex_generate_call_id(self, src: str, dst: str, req_type: str) -> str:
        call_details: str = libcpex.normalize_call_details(src=src, dst=dst)
        
        self.log_msg(f'--> Generates Call Details: {call_details}')
        requests, masks = libcpex.create_evaluation_requests(call_details, n_ev=self.n_ev, gsk=self.gsk, gpk=self.gpk)
        self.log_msg(f'--> Created Requests for the Following EVs: {[r["nodeId"] for r in requests]}')
        
        req_time_start = time.perf_counter()
        responses = await self.make_request('evaluate', requests=requests)
        req_time_taken = time.perf_counter() - req_time_start
        
        times_taken = [r['time_taken'] for r in responses if 'time_taken' in r]
        ev_avg_time = sum(times_taken) / len(times_taken) if len(times_taken) else 0 # Average time taken to evaluate a single request by an EV
        
        if req_type == 'publish':
            self.publish_ev_time = ev_avg_time
            self.publish_provider_time -= req_time_taken # Subtract wait time from compute time
        if req_type == 'retrieve':
            self.retrieve_ev_time = ev_avg_time
            self.retrieve_provider_time -= req_time_taken # Subtract wait time from compute time
        
        call_id = libcpex.create_call_id(responses=responses, masks=masks)
        if call_id and type(call_id) == bytes:
            self.log_msg(f"---> Call ID: {Utils.to_base64(call_id)}")
        return call_id

    async def cpex_retrieve(self, src: str, dst: str) -> str:
        call_id = await self.cpex_generate_call_id(src=src, dst=dst, req_type='retrieve')
        
        if not call_id:
            return None
        
        reqs = libcpex.create_retrieve_requests(call_id=call_id, n_ms=self.n_ms, gsk=self.gsk, gpk=self.gpk)
        
        req_time_start = time.perf_counter()
        responses = await self.make_request('retrieve', requests=reqs)
        req_time_taken = time.perf_counter() - req_time_start
        
        self.retrieve_provider_time -= req_time_taken # Subtract wait time from compute time
        
        self.retrieve_ms_time = req_time_taken / len(reqs) # Average time taken to store a message by a single store
        
        responses = [r for r in responses if '_error' not in r]
        token = libcpex.decrypt(call_id=call_id, responses=responses, src=src, dst=dst, gpk=self.gpk)
        return token
    
    async def make_request(self, req_type: str, requests: List[dict]):
        if self.fake_proxy:
            return await make_fake_request(
                req_type=req_type, 
                requests=requests,
                gsk=self.gsk,
                gpk=self.gpk
            )
        else:
            return await http.posts(reqs=requests)
    
    def get_publish_compute_times(self):
        return {
            'provider': misc.toMs(self.publish_provider_time),
            'evaluator': misc.toMs(self.publish_ev_time),
            'message_store': misc.toMs(self.publish_ms_time),
        }

    def get_retrieve_compute_times(self):
        return {
            'provider': misc.toMs(self.retrieve_provider_time),
            'evaluator': misc.toMs(self.retrieve_ev_time),
            'message_store': misc.toMs(self.retrieve_ms_time),
        }
    
    def log_msg(self, msg):
        if config.DEBUG and self.logger:
            self.logger.debug(msg)
            
async def make_fake_request(req_type: str, requests: List[dict], gsk: str, gpk: str):
    if req_type == 'evaluate':
        return fake_ev_evaluate(requests=requests, gsk=gsk, gpk=gpk)
    elif req_type == 'publish':
        return fake_ms_publish(requests=requests, gsk=gsk, gpk=gpk)
    elif req_type == 'retrieve':
        return fake_ms_retrieve(requests=requests, gsk=gsk, gpk=gpk)
        
def fake_ev_evaluate(requests: List[dict], gsk: str, gpk: str):
    responses = []
    sk, pk = Oprf.keygen()
    for request in requests:
        fx, vk = Oprf.evaluate(sk, pk, Utils.from_base64(request['data']['x']))
        responses.append({ "fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk) })
    return responses

def fake_ms_publish(requests: List[dict], gsk: str, gpk: str):
    responses = []
    for request in requests:
        responses.append({'_success': 'message stored'})
    return responses

def fake_ms_retrieve(requests: List[dict], gsk: str, gpk: str):
    responses = []
    for request in requests:
        responses.append({
            'idx': 'dbzv7wD3D0lTtM1l/RfRTWKTnDMXqgRk3Epwp2Mh+qk=', 
            'ctx': 'Hlnv8bLedWZKWaNGSE74HXfKMV4kybw1WtM4jwhlAjU=:OLFjsWrGV/vbuF2T8tzzKQ4Ha1NXa3DcEa4o3+OKovf2kLdEvMJ/cY/IoVOZsbICPwwCSGEcMe6uUCclg+oaMYFDZISdOp0Xski5cyD7W5NKcuIkJANUJu0FXcRGOfACTQTs9jhgOHmWGuQmyvfvcG2tMJFGupYlaXezC9P3avN7cDK+w+6gHgYXOd5yWdBg/MxtZ8oK9XR6pAWbXgWKyKA2UzqYQj9yKYhebBJfAg3O4nojlYsAWGhHnunAMGI32HjIesGRnXthxDV+TjT/9D96FVy+7V9K38Ri7T1tFG1j27ySiUAuVdWjOW5UjS83OQNigkwiiQYkvyvo/NMSqWjB03n5ja82CqWt1nI6yLvIRuSGJU2X+a665JGWEHndRa5UsYTUPu+fpc6tuBC1Mwl9HE73cNKtCYa4ewR5MVnrXFhNX96aKJMvAJU6QUR7GShZnoI1Rvobu9nil7gn2ulki/w=', 
            'sig': 'ATAAAAAh2WRbHPXWLJLt00kSTAjgjqm7N+3yaz0VpJ64tGhuOFtaKFu0T5pzEG8GXVv+9oMwAAAAuad5cXhfksh5OkIW6o0CXjnDtPk3enuy48KhcoYsy3z4tSFs7feyU6xQ5RaWhaSKMAAAAK7dD3uyb0jD4N7E0HHrug4Zfu/2iUysyNCu3f8NUbSJKnR4zPZ839iZEPsP0+WMiiAAAAAI+vgnAxgf8URFEmKb//m9gJB+lRuJscoqSPHyrY5mIiAAAAD59QI/ImkNFB5jlAyz83mlWJ3ufykC02OLq7AgjaATDyAAAABVn1qiqknCxJerwNA9tbIvqcNgIGEX3AMJTDtzBS4lSyAAAABS5i5yic69ZxXu9WYnyw9fTzjMxE4Zz666sD4znS/oVSAAAACPS68QLVG00j/L8x5DI30M48PDK4XXYF1dXspMdGapPCAAAACHxFj3DH0pHg58QNrQfurI2xrrdi2zMSXQQTKqxUchSQ=='
        })
    return responses