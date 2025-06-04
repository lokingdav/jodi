import json, os, time
from typing import List
from jodi.crypto import libjodi, groupsig, billing
from jodi.models import cache
from jodi import config
from pylibjodi import Oprf, Utils
from jodi.prototype.provider import Provider as BaseProvider

evKeySets = None

def set_evaluator_keys(keys: dict):
    global evKeySets
    evKeySets = {}
    if not keys:
        return
    for nodeId in keys:
        evKeySets[nodeId] = []
        for key in keys[nodeId]:
            sk, vk = key.split('.')
            evKeySets[nodeId].append((Utils.from_base64(sk), Utils.from_base64(vk)))
    
def get_evaluator_keyset(nodeId: str):
    return evKeySets.get(nodeId, None)

class MessageStore:
    def __init__(self, nodeId: str, gpk, available: bool, logger):
        self.gpk = gpk
        self.nodeId = nodeId
        self.name = f'sim.ms.{nodeId}'
        self.available = available
        self.logger = logger

    def log_msg(self, msg):
        if config.DEBUG and self.logger:
            self.logger.debug(f"--> {self.nodeId}: {msg}")

    def get_content_key(self, idx: str):
        return f'{self.name}.{idx}'
    
    def publish(self, request: dict):
        if not self.available:
            res = {'_error': 'node not available'}
            self.log_msg(res)
            return res
        
        start_time = time.perf_counter()
        
        if not billing.verify_token(config.VOPRF_VK, request['bt']):
            res = {'_error': 'invalid billing token', 'time_taken': time.perf_counter() - start_time}
            self.log_msg(res)
            return res
        
        pp = Utils.to_base64(Utils.hash256(bytes(request['idx'] + request['ctx'], 'utf-8')))
        bb = billing.get_billing_hash(request['bt'], request['peers'])

        if not groupsig.verify(sig=request['sig'], msg=pp + bb, gpk=self.gpk):
            res = {'_error': 'invalid signature', 'time_taken': time.perf_counter() - start_time}
            self.log_msg(res)
            return res
         
        value = request['idx'] + '.' + request['ctx'] + '.' + request['sig'] + '.' + bb

        cache.cache_for_seconds(
            key=self.get_content_key(request['idx']), 
            value=value, 
            seconds=config.T_MAX_SECONDS
        )
        
        return {'_success': 'message stored', 'time_taken': time.perf_counter() - start_time}
    
    def retrieve(self, request: dict):
        if not self.available:
            res = {'_error': 'node not available'}
            self.log_msg(res)
            return res
        
        start_time = time.perf_counter()

        if not billing.verify_token(config.VOPRF_VK, request['bt']):
            res = {'_error': 'invalid billing token', 'time_taken': time.perf_counter() - start_time}
            self.log_msg(res)
            return res
        
        pp = Utils.to_base64(Utils.hash256(bytes(request['idx'], 'utf-8')))
        bb = billing.get_billing_hash(request['bt'], request['peers'])
        
        if not groupsig.verify(sig=request['sig'], msg=pp + bb, gpk=self.gpk):
            res = {'_error': 'invalid signature', 'time_taken': time.perf_counter() - start_time}
            self.log_msg(res)
            return res

        value = cache.find(key=self.get_content_key(request['idx']))
        
        if not value:
            return {'_error': 'message not found', 'time_taken': time.perf_counter() - start_time}
        
        (msidx, msctx, mssig, bill_h) = value.split('.')
        
        return {'idx': msidx, 'ctx': msctx, 'sig': mssig, 'bb': bill_h, 'time_taken': time.perf_counter() - start_time}

class Evaluator:
    @staticmethod
    def create_keyset():
        keys = []
        for _ in range(config.KEYLIST_SIZE):
            sk, vk  = Oprf.keygen()
            keys.append(Utils.to_base64(sk) + '.' + Utils.to_base64(vk))
        return keys
        
    def __init__(self, nodeId: str, gpk, available: bool, logger):
        self.gpk = gpk
        self.nodeId = nodeId
        self.logger = logger
        self.available = available
        self.keys = get_evaluator_keyset(nodeId)

    def log_msg(self, msg):
        if config.DEBUG and self.logger:
            self.logger.debug(f"--> {self.nodeId}: {msg}")

    def evaluate(self, request: dict):
        if not self.available:
            res = {'_error': 'node not available'}
            self.log_msg(res)
            return res
        
        start_time = time.perf_counter()

        if not billing.verify_token(config.VOPRF_VK, request['bt']):
            res = {'_error': 'invalid billing token', 'time_taken': time.perf_counter() - start_time}
            self.log_msg(res)
            return res

        pp = Utils.to_base64(Utils.hash256(bytes(str(request['i_k']) + request['x'], 'utf-8')))
        bb = billing.get_billing_hash(request['bt'], request['peers'])
        
        if not groupsig.verify(sig=request['sig'], msg=pp + bb, gpk=self.gpk):
            res = {'_error': 'invalid signature', 'time_taken': time.perf_counter() - start_time}
            self.log_msg(res)
            return res
        
        self.log_msg(f"Receives i_k={request['i_k']}, x={request['x']}")
        self.log_msg(f"Uses sk={Utils.to_base64(self.keys[request['i_k']][0])}, pk={Utils.to_base64(self.keys[request['i_k']][1])}")
        
        (fx, vk) = Oprf.evaluate(self.keys[request['i_k']][0], self.keys[request['i_k']][1], Utils.from_base64(request['x']))
        return [{"fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk), 'time_taken': time.perf_counter() - start_time}]
    

class Provider(BaseProvider):
    def __init__(self, params: dict):
        super().__init__(params=params)
    
    async def make_request(self, req_type, requests):
        responses = []
        timer = time.perf_counter()
        for req in requests:
            available = req.get('avail')
            available = available['up'] if available is not None else True
            
            if req_type == 'evaluate':
                payload = Evaluator(
                    nodeId=req['nodeId'], 
                    gpk=self.gpk, 
                    available=available,
                    logger=self.logger
                ).evaluate(req['data'])
            elif req_type == 'publish':
                payload = MessageStore(
                    nodeId=req['nodeId'], 
                    gpk=self.gpk, 
                    available=available,
                    logger=self.logger
                ).publish(req['data'])
            elif req_type == 'retrieve':
                payload = MessageStore(
                    nodeId=req['nodeId'], 
                    gpk=self.gpk, 
                    available=available,
                    logger=self.logger
                ).retrieve(req['data'])
                
            responses.append(payload)
        
        # This section makes it appear as if the requests were parallelized
        n = len(responses)
        time_taken = time.perf_counter() - timer
        avg_time_taken = time_taken/n
        self.sim_overhead.append(time_taken - avg_time_taken)
        return responses