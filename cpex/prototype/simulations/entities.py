import json, os, time
from typing import List
from cpex.crypto import libcpex, groupsig
from cpex.models import cache
from cpex import config
from pylibcpex import Oprf, Utils
from cpex.prototype.provider import Provider as BaseProvider

evKeySets = None

def set_evaluator_keys(keys: dict):
    global evKeySets
    evKeySets = {}
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
            self.log_msg("Error -- node not available")
            return {'_error': 'node not available'}
        
        if not groupsig.verify(sig=request['sig'], msg=request['idx'] + request['ctx'], gpk=self.gpk):
            self.log_msg("Error -- invalid signature")
            return {'_error': 'invalid signature'}
         
        value = request['idx'] + '.' + request['ctx'] + '.' + request['sig']

        cache.cache_for_seconds(
            key=self.get_content_key(request['idx']), 
            value=value, 
            seconds=config.REC_TTL_SECONDS
        )

        return {'_success': 'message stored'}
    
    def retrieve(self, request: dict):
        if not self.available:
            self.log_msg("Error -- node not available")
            return {'_error': 'node not available'}
        
        if not groupsig.verify(sig=request['sig'], msg=request['idx'], gpk=self.gpk):
            self.log_msg("Error -- invalid signature")
            return {'_error': 'invalid signature'}

        value = cache.find(key=self.get_content_key(request['idx']))
        
        if not value:
            return {'_error': 'message not found'}
        
        (msidx, msctx, mssig) = value.split('.')

        return {'idx': msidx, 'ctx': msctx, 'sig': mssig}

class Evaluator:
    @staticmethod
    def create_keyset():
        keys = []
        for _ in range(config.OPRF_KEYLIST_SIZE):
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
        start_time = time.perf_counter()
        if not self.available:
            self.log_msg("Error -- node not available")
            return {'_error': 'node not available'}
        
        if not groupsig.verify(sig=request['sig'], msg=str(request['i_k']) + request['x'], gpk=self.gpk):
            self.log_msg("Error -- invalid signature")
            return {'_error': 'invalid signature'}
        
        self.log_msg(f"Receives i_k={request['i_k']}, x={request['x']}")
        self.log_msg(f"Uses sk={Utils.to_base64(self.keys[request['i_k']][0])}, pk={Utils.to_base64(self.keys[request['i_k']][1])}")
        
        (fx, vk) = Oprf.evaluate(self.keys[request['i_k']][0], self.keys[request['i_k']][1], Utils.from_base64(request['x']))
        time_taken = time.perf_counter() - start_time
        return {"fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk), 'time_taken': time_taken}
    

class Provider(BaseProvider):
    def __init__(self, params: dict):
        super().__init__(params=params)
    
    async def make_request(self, req_type, requests):
        responses = []
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
        return responses