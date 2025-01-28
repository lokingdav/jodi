import json, os
from typing import List
from cpex.crypto import libcpex, groupsig
from cpex.models import cache
from cpex import config
from pylibcpex import Oprf, Utils
from cpex.prototype.provider import Provider as BaseProvider

# cache_client = None

# def set_cache_client(client):
#     global cache_client
#     cache_client = client

class MessageStore:
    def __init__(self, nodeId: str, gpk, available: bool, cache_client, logger):
        self.gpk = gpk
        self.nodeId = nodeId
        self.name = f'sim.ms.{nodeId}'
        self.cache_client = cache_client
        self.available = available
        self.logger = logger

    def log_msg(self, msg):
        if config.DEBUG:
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
            client=self.cache_client, 
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

        value = cache.find(
            client=self.cache_client, 
            key=self.get_content_key(request['idx'])
        )
        
        if not value:
            return {'_error': 'message not found'}
        
        (msidx, msctx, mssig) = value.split('.')

        return {'idx': msidx, 'ctx': msctx, 'sig': mssig}

class Evaluator:
    def __init__(self, nodeId: str, gpk, available: bool, cache_client, logger):
        self.gpk = gpk
        self.nodeId = nodeId
        self.name = f'sim.ev.{nodeId}'
        self.cache_client = cache_client
        self.available = available
        self.set_keys()
        self.logger = logger

    def set_keys(self):
        keys = cache.find(client=self.cache_client, key=self.name, dtype=dict)
        if keys:
            self.keys = []
            for item in keys:
                sk, vk = item.split('.')
                self.keys.append((Utils.from_base64(sk), Utils.from_base64(vk)))
            if len(self.keys) != config.OPRF_KEYLIST_SIZE:
                self.init_keys()
        else:
            self.init_keys()

    def init_keys(self):
        self.keys = [Oprf.keygen() for _ in range(config.OPRF_KEYLIST_SIZE)]
        keys = json.dumps([Utils.to_base64(sk) + '.' + Utils.to_base64(vk) for (sk, vk) in self.keys])
        cache.save(client=self.cache_client, key=self.name, value=keys)

    def log_msg(self, msg):
        if config.DEBUG:
            self.logger.debug(f"--> {self.nodeId}: {msg}")

    def evaluate(self, request: dict):
        if not self.available:
            self.log_msg("Error -- node not available")
            return {'_error': 'node not available'}
        
        if not groupsig.verify(sig=request['sig'], msg=str(request['i_k']) + request['x'], gpk=self.gpk):
            self.log_msg("Error -- invalid signature")
            return {'_error': 'invalid signature'}
        
        self.log_msg(f"Receives i_k={request['i_k']}, x={request['x']}")
        self.log_msg(f"Uses sk={Utils.to_base64(self.keys[request['i_k']][0])}, pk={Utils.to_base64(self.keys[request['i_k']][1])}")
        
        (fx, vk) = Oprf.evaluate(self.keys[request['i_k']][0], self.keys[request['i_k']][1], Utils.from_base64(request['x']))

        return {"fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk)}
    

class Provider(BaseProvider):
    def __init__(self, params: dict, cache_client):
        self.cache_client = cache_client
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
                    cache_client=self.cache_client,
                    logger=self.logger
                ).evaluate(req['data'])
            elif req_type == 'publish':
                payload = MessageStore(
                    nodeId=req['nodeId'], 
                    gpk=self.gpk, 
                    available=available,
                    cache_client=self.cache_client,
                    logger=self.logger
                ).publish(req['data'])
            elif req_type == 'retrieve':
                payload = MessageStore(
                    nodeId=req['nodeId'], 
                    gpk=self.gpk, 
                    available=available,
                    cache_client=self.cache_client,
                    logger=self.logger
                ).retrieve(req['data'])
                
            responses.append(payload)
        return responses