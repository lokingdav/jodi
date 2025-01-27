import random, traceback, time, os
from uuid import uuid4
from pydantic import BaseModel
import cpex.config as config
import cpex.constants as constants
from cpex.helpers import misc, http, files
from cpex.prototype.stirshaken.auth_service import AuthService
from typing import List, Union
from cpex.crypto import libcpex
from cpex.models import persistence, cache
from cpex.prototype.stirshaken import stirsetup
from pylibcpex import Utils

def get_type(instance):
    return 'SIP Signal' if isinstance(instance, SIPSignal) else 'TDM Signal'

class TDMSignal(BaseModel):
    Pid: str
    To: str
    From: str

class SIPSignal(BaseModel):
    Pid: str
    To: str
    From: str
    Identity: str
    CallId: str = str(uuid4())

class Provider:
    def __init__(self, params: dict):
        self.latencies = []
        self.pid = params['pid']
        self.SPC = f'sp_{self.pid}'
        self.impl = params['impl']
        self.mode = params['mode']
        self.gpk = params['gpk']
        self.gsk = params['gsk']
        self.n_ev = params['n_ev']
        self.n_ms = params['n_ms']
        self.logger = params.get('logger')
        self.next_prov = params.get('next_prov')
        self.cps_fqdn = params.get('cps_fqdn')
        self.cr_fqdn = params.get('cr_fqdn')

        if self.mode not in ['atis', 'cpex']:
            raise Exception('Mode must be specified as either atis or cpex')
        
        if config.is_atis_mode(self.mode):
            if not self.cps_fqdn:
                raise Exception('CPS FQDN must be specified')
            if not self.cr_fqdn:
                raise Exception('CR FQDN must be specified')
            
        self.load_auth_service()

    def log_msg(self, msg):
        if config.DEBUG and self.logger:
            self.logger.debug(msg)
    
    def is_atis_mode(self):
        return config.is_atis_mode(self.mode)
    
    def get_latency(self):
        return round(sum(self.latencies), 4)
    
    def get_latency_ms(self):
        return round(self.get_latency() * 1000, 2)
    
    def next_prov_is_capable(self):
        return self.next_prov and self.next_prov[1] == 1

    def load_auth_service(self):
        credential = persistence.get_credential(name=self.SPC)
        if not credential:
            credential = stirsetup.issue_cert(name=self.SPC, ctype='sp')
        self.auth_service = AuthService(
            ownerId=self.pid,
            private_key_pem=credential[constants.PRIV_KEY],
            x5u=f'http://{self.cr_fqdn}/certs/{self.SPC}'
        )
        
    async def forward_call(self, signal: Union[SIPSignal, TDMSignal]):
        if not self.impl or not self.next_prov_is_capable():
            signal: TDMSignal = await self.publish(sip_signal=signal)
        
        self.log_msg(f'--> FORWARDS {get_type(signal)} to {self.next_prov}')
        
        return signal
    
    async def originate(self, src: str = None, dst: str = None) -> Union[SIPSignal, TDMSignal]:
        src = misc.fake_number(1) if src is None else src
        dst = misc.fake_number(1) if dst is None else dst
        attest = random.choice(['A', 'B', 'C'])
        
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, cps={self.cps_fqdn}) ORIGINATES Call From src={src} to dst={dst} with attest={attest}')
        token = self.auth_service.create_passport(orig=src, dest=dst, attest=attest)
        signal = {'To': dst, 'From': src, 'Pid': self.pid}
        signal = SIPSignal(**signal, Identity=token)
        signal = await self.forward_call(signal)
            
        return signal, token
    
    async def receive(self, incoming_signal: Union[SIPSignal, TDMSignal]) -> Union[SIPSignal, TDMSignal]:
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, cps={self.cps_fqdn}) RECEIVES {get_type(incoming_signal)}')
        
        if isinstance(incoming_signal, TDMSignal):
            if not self.impl or not self.next_prov_is_capable():
                return self.convert_tdm_to_tdm(incoming_signal)
            
            return await self.retrieve(incoming_signal)

        if isinstance(incoming_signal, SIPSignal):
            if incoming_signal.Identity:
                if self.next_prov_is_capable():
                    return self.convert_sip_to_sip(incoming_signal)
                else:
                    return await self.publish(incoming_signal)
            else:
                if self.next_prov_is_capable():
                    return await self.retrieve(incoming_signal)
                else:
                    return self.convert_sip_to_tdm(incoming_signal)
    
    async def terminate(self, incoming_signal: Union[SIPSignal, TDMSignal]):
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, cps={self.cps_fqdn}) TERMINATES {get_type(incoming_signal)}')

        if isinstance(incoming_signal, SIPSignal) and incoming_signal.Identity:
            return incoming_signal.Identity
        
        terminated_signal: SIPSignal = await self.retrieve(signal=incoming_signal)

        self.log_msg('--> Call Terminated')
        return terminated_signal.Identity
        
    async def publish(self, sip_signal: SIPSignal) -> TDMSignal:
        tdm_signal = self.convert_sip_to_tdm(signal=sip_signal)
        
        if not sip_signal.Identity:
            return tdm_signal
        
        self.log_msg(f'--> Executes PUBLISH')
        
        start_time = time.perf_counter()
        
        if self.is_atis_mode():
            await self.atis_publish(signal=sip_signal)
        else:
            await self.cpex_publish(signal=sip_signal)
            
        self.latencies.append(time.perf_counter() - start_time)
        
        return tdm_signal
        
    async def atis_publish(self, signal: SIPSignal):
        authorization: str = self.auth_service.authenticate_request(
            action='publish',
            orig=signal.From,
            dest=signal.To,
            passports=[signal.Identity],
            iss=self.pid,
            aud=self.cps_fqdn
        )
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        payload: dict = {'passports': [ signal.Identity ]}
        url: str = f'http://{self.cps_fqdn}/publish/{signal.To}/{signal.From}'
        await http.posts(reqs=[{'url': url, 'data': payload, 'headers': headers}])
        
    async def cpex_publish(self, signal: SIPSignal):
        # Call ID generation
        call_id = await self.cpex_call_id_generation(signal=signal, req_type=f'Publish by {self.pid}')
        
        if not call_id:
            return
        
        # Encrypt and MAC, then sign the requests
        reqs = libcpex.create_storage_requests(
            call_id=call_id, 
            msg=signal.Identity,
            n_ms=self.n_ms,
            gsk=self.gsk,
            gpk=self.gpk
        )

        self.log_msg(f'--> Created Requests for the Following MSs: {[r["nodeId"] for r in reqs]}')
        
        responses = await self.make_request('publish', requests=reqs)
        self.log_msg(f'--> Responses: {responses}')
    
    async def retrieve(self, signal: TDMSignal) -> SIPSignal:
        self.log_msg(f'--> Executes RETRIEVE')
        try: 
            start_time = time.perf_counter()
            if self.is_atis_mode():
                token = await self.atis_retrieve_token(signal=signal)
            else:
                token = await self.cpex_retrieve_token(signal=signal)
            self.latencies.append(time.perf_counter() - start_time)
            
            signal = self.convert_tdm_to_sip(signal=signal, token=token)
        except Exception as e:
            self.log_msg(f'Error while executing RETRIEVE: {e}')
            traceback.print_exc()
            signal = self.convert_tdm_to_sip(signal=signal)
        return signal
    
    async def atis_retrieve_token(self, signal: TDMSignal) -> List[str]:
        authorization: str = self.auth_service.authenticate_request(
            action='retrieve',
            orig=signal.From,
            dest=signal.To,
            passports=[],
            iss=self.pid,
            aud=self.cps_fqdn
        )
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        url: str = f'http://{self.cps_fqdn}/retrieve/{signal.To}/{signal.From}'
        response = await http.get(url=url, params={}, headers=headers)
        return response
    
    async def cpex_call_id_generation(self, signal: Union[SIPSignal, TDMSignal], req_type: str) -> str:
        call_details: str = libcpex.normalize_call_details(src=signal.From, dst=signal.To)
        self.log_msg(f'--> Generates Call Details: {call_details}')
        requests, masks = libcpex.create_evaluation_requests(call_details, n_ev=self.n_ev, gsk=self.gsk, gpk=self.gpk)
        self.log_msg(f'--> Created Requests for the Following EVs: {[r["nodeId"] for r in requests]}')
        
        responses = await self.make_request('evaluate', requests=requests)
        call_id = libcpex.create_call_id(responses=responses, masks=masks)
        if call_id and type(call_id) == bytes:
            self.log_msg(f"---> Call ID: {Utils.to_base64(call_id)}")
        return call_id

    async def cpex_retrieve_token(self, signal: TDMSignal) -> str:
        call_id = await self.cpex_call_id_generation(signal=signal, req_type=f'Retrieve by {self.pid}')
        
        if not call_id:
            return None
        
        reqs = libcpex.create_retrieve_requests(call_id=call_id, n_ms=self.n_ms, gsk=self.gsk, gpk=self.gpk)
        responses = await self.make_request('retrieve', requests=reqs)
        responses = [r for r in responses if '_error' not in r]
        token = libcpex.decrypt(call_id=call_id, responses=responses, src=signal.From, dst=signal.To, gpk=self.gpk)
        return token
            
    def convert_sip_to_tdm(self, signal: SIPSignal):
        if not isinstance(signal, SIPSignal):
            raise Exception('Signal must be an instance of SIPSignal class')

        return TDMSignal(**{
            'To': signal.To,
            'From': signal.From,
            'Pid': self.pid
        })
    
    def convert_tdm_to_sip(self, signal: TDMSignal, token: str = ''):
        if not isinstance(signal, TDMSignal):
            raise Exception('Signal must be an instance of TDMSignal class')
        
        return SIPSignal(**{
            'To': signal.To,
            'From': signal.From,
            'Pid': self.pid,
            'Identity': token if token else ''
        })
    
    def convert_sip_to_sip(self, signal: SIPSignal) -> SIPSignal:
        if not isinstance(signal, SIPSignal):
            raise Exception('Signal must be an instance of SIPSignal class')
        
        return SIPSignal(**{
            'To': signal.To,
            'From': signal.From,
            'Pid': self.pid,
            'Identity': signal.Identity
        })
    
    def convert_tdm_to_tdm(self, signal: TDMSignal) -> TDMSignal:
        if not isinstance(signal, TDMSignal):
            raise Exception('Signal must be an instance of TDMSignal class')
        
        return TDMSignal(**{
            'To': signal.To,
            'From': signal.From,
            'Pid': self.pid
        })
    
    async def make_request(self, req_type: str, requests: List[dict]):
        responses = await http.posts(reqs=requests)
        return responses