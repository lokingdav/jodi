import time
import cpex.config as config
from cpex.helpers import misc, http
from typing import List
from cpex.crypto import libcpex
from pylibcpex import Utils

class CpexIWF:
    def __init__(self, params: dict):
        self.logger = params.get('logger')
        self.n_ev = params['n_ev']
        self.n_ms = params['n_ms']
        self.gpk = params['gpk']
        self.gsk = params['gsk']
        self.mode = params['mode']
        
        # Providers compute time
        self.publish_provider_time = 0
        self.retrieve_provider_time = 0
        
        # Evaluators compute time
        self.publish_ev_time = 0
        self.retrieve_ev_time = 0
        
        # Message stores compute time
        self.publish_ms_time = 0
        self.retrieve_ms_time = 0
        
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
        responses = await http.posts(reqs=requests)
        return responses