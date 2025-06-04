import time
import jodi.config as config
from jodi.helpers import misc, http
from typing import List
from jodi.crypto import libjodi, groupsig, audit_logging
from pylibjodi import Utils, Oprf
import numpy as np
from jodi.prototype.stirshaken import certs

class JodiIWF:
    def __init__(self, params: dict):
        self.n_ev = params['n_ev']
        self.n_ms = params['n_ms']
        self.gpk = params['gpk']
        self.gsk = params['gsk']
        self.ipk = certs.get_public_key_from_cert(config.TEST_ICERT)
        self.logger = params.get('logger')
        self.metrics_logger = params.get('metrics_logger')
        self.fake_proxy = params.get('fake_proxy', False)
        self.bt = params['bt']
        self.sim_overhead = []
        
        self.reset()
        
    def reset(self):
        """Resets compute times which does not include wait times"""
        self.publish_provider_time = 0
        self.retrieve_provider_time = 0
        
        self.publish_ev_time = 0
        self.retrieve_ev_time = 0
        
        self.publish_ms_time = 0
        self.retrieve_ms_time = 0
        
        self.sim_overhead = []
        
    async def jodi_generate_call_ids(self, src: str, dst: str, req_type: str) -> str:
        start_compute = time.perf_counter()

        self.log_msg(f'==================== CALL ID GENERATION')
        self.log_msg(f'--> This is call id generation for {req_type} request')
        call_details: str = libjodi.normalize_call_details(src=src, dst=dst)
        self.log_msg(f'--> Generates Call Details: {call_details}')
        requests, mask, hreq = libjodi.create_evaluation_requests(
            call_details, 
            n_ev=self.n_ev, 
            gsk=self.gsk, 
            gpk=self.gpk,
            bt=self.bt
        )
        self.log_msg(f'--> Created Requests for the Following EVs: {[r["nodeId"]+":::"+str(r["data"]["i_k"]) for r in requests]}')
        
        end_compute = time.perf_counter()
        responses = await self.make_request('evaluate', requests=requests)
        req_time_taken = time.perf_counter() - end_compute
        
        self.log_msg(f'--> Responses from Evaluators: {responses}')
        
        # Average time taken to evaluate a single request by an EV
        try:
            sim_ovrhd = time.perf_counter()
            flattened = []
            for reslist in responses:
                if type(reslist) == dict:
                    flattened.append(reslist.get('time_taken', 0))
                elif type(reslist) == list:
                    flattened.extend([res.get('time_taken', 0) for res in reslist])
            ev_avg_time = np.mean(flattened)
            sim_ovrhd = time.perf_counter() - sim_ovrhd
        except Exception as e:
            pass
        
        if req_type == 'publish':
            self.publish_ev_time = ev_avg_time
            self.publish_provider_time -= req_time_taken # Subtract wait time from compute time
            self.publish_provider_time -= sim_ovrhd # Subtract simulation overhead
        if req_type == 'retrieve':
            self.retrieve_ev_time = ev_avg_time
            self.retrieve_provider_time -= req_time_taken # Subtract wait time from compute time
            self.retrieve_provider_time -= sim_ovrhd # Subtract simulation overhead
            
        self.sim_overhead.append(sim_ovrhd)
        
        compute_time = end_compute - start_compute
        net_time = req_time_taken
        
        start_compute = time.perf_counter()
        self.log_msg(f"--> Validating EV Responses")
        
        valid_responses = []
        for response in responses:
            hres = Utils.to_base64(Utils.hash256(bytes(misc.stringify(response['evals']), 'utf-8')))
            if audit_logging.ecdsa_verify(public_key=self.ipk, data=hreq+hres, sigma=response['sig_r']):
                valid_responses.append(response['evals'])
                
        self.log_msg(f'--> Valid Responses: {valid_responses}')
        
        call_ids = libjodi.create_call_ids(
            responses=valid_responses, 
            mask=mask, 
            req_type=req_type,
            call_details=call_details
        )
        
        compute_time += time.perf_counter() - start_compute
        
        if call_ids:
            self.log_msg(f"---> Call ID: {[Utils.to_base64(cid) for cid in call_ids if cid]}")
        else:
            self.log_msg(f'--> No Call ID generated')

        self.log_msg(f'==================== END CALL ID GENERATION')
        
        runtime = {
            'compute_time': compute_time,
            'net_time': net_time,
        }
        
        return call_ids, runtime
    
    async def jodi_publish(self, src, dst, token):
        self.log_msg(f'===== START PUBLISH PROTOCOL =====')
        call_ids, cid_runtime = await self.jodi_generate_call_ids(src=src, dst=dst, req_type='publish')
        
        if not call_ids:
            self.log_msg(f'===== END PUBLISH because no call id generated =====')
            return {'_error': 'No Call ID generated'}
        
        start_compute = time.perf_counter()
        
        reqs = libjodi.create_storage_requests(
            call_id=call_ids[0], # Only publish the recent call ID
            msg=token,
            n_ms=self.n_ms,
            gsk=self.gsk,
            gpk=self.gpk,
            bt=self.bt
        )
        self.log_msg(f'--> Created Requests for the Following MSs: {[r["nodeId"] for r in reqs]}')
        
        end_compute = time.perf_counter()
        responses = await self.make_request('publish', requests=reqs)
        req_time_taken = time.perf_counter() - end_compute
        self.log_msg(f'--> Responses From MS: {responses}')
        
        try:
            sim_ovrhd = time.perf_counter()
            # Subtract wait time from compute time
            self.publish_provider_time -= req_time_taken
            # Average time taken to store a message by a single store
            self.publish_ms_time = np.mean([res.get('time_taken', 0) for res in responses])
            self.sim_overhead.append(time.perf_counter() - sim_ovrhd)
        except:
            pass
        self.log_msg(f'===== END PUBLISH PROTOCOL =====\n')
        
        compute_time = cid_runtime['compute_time'] + (end_compute - start_compute)
        net_time = cid_runtime['net_time'] + req_time_taken
        self.log_metric(f'jodi,publish,{misc.toMs(compute_time)},{misc.toMs(net_time)},{misc.toMs(compute_time + net_time)}')
        
        return {'_success': 'message published'}

    async def jodi_retrieve(self, src: str, dst: str) -> str:
        self.log_msg(f'===== START RETRIEVE PROTOCOL =====')
        call_ids, cid_runtime = await self.jodi_generate_call_ids(src=src, dst=dst, req_type='retrieve')
        
        if not call_ids:
            self.log_msg(f'===== END RETRIEVE PROTOCOL because no call id generated =====')
            return None
        
        start_compute = time.perf_counter()
        requests = libjodi.create_retrieve_requests(
            call_ids=call_ids, 
            n_ms=self.n_ms, 
            gsk=self.gsk, 
            gpk=self.gpk,
            bt=self.bt
        )
        # self.log_msg(f'--> Retrieve Requests: {requests}')
        self.log_msg(f'--> Created Retrieve Requests for the Following MSs: {[r["nodeId"] for r in requests]}')
        
        end_compute = time.perf_counter()
        responses = await self.make_request('retrieve', requests=requests)
        req_time_taken = time.perf_counter() - end_compute
        self.log_msg(f'--> Responses from Stores: {responses}')
        
        self.retrieve_provider_time -= req_time_taken # Subtract wait time from compute time
        
        self.retrieve_ms_time = np.mean([res.get('time_taken', 0) for res in responses]) # Average time taken to store a message by a single store
        
        compute_time = cid_runtime['compute_time'] + (end_compute - start_compute)
        net_time = cid_runtime['net_time'] + req_time_taken
        
        # self.log_msg(f"\n--> Filtered Responses: {responses}")
        # self.log_msg(f"--> Call IDs: {call_ids}\n")
        start_compute = time.perf_counter()
        token = libjodi.decrypt(call_ids=call_ids, responses=responses, gpk=self.gpk, ipk=self.ipk)
        compute_time += time.perf_counter() - start_compute
        
        self.log_msg(f'--> Retrieved Token: {token}')
        self.log_msg(f"===== END RETRIEVE PROTOCOL =====\n")
        
        self.log_metric(f'jodi,retrieve,{misc.toMs(compute_time)},{misc.toMs(net_time)},{misc.toMs(compute_time + net_time)}')
        
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
            if req_type == 'retrieve':
                return await http.posts_race(reqs=requests)
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

    def log_metric(self, metric: str):
        if self.metrics_logger:
            self.metrics_logger.info(metric)
            
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
        responses.append([{ "fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk) }])
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