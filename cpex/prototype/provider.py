import random, traceback, time
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
    def __init__(self, pid: str, impl: bool, mode: str, cps_url: str = None, log: bool = True, gsk=None, gpk = None):
        self.pid = pid
        self.impl = impl
        self.mode = mode
        self.cps_fqdn = None
        self.cps_url = cps_url
        self.load_auth_service()
        self.latencies: list = []
        self.log = log
        self.gpk = gpk
        self.gsk = gsk

        if self.cps_url:
            self.cps_fqdn = cps_url.replace('http://', '').replace('https://', '').split(':')[0]

    def log_msg(self, msg):
        if self.log:
            print(msg)
    
    def is_atis_mode(self):
        return config.is_atis_mode(self.mode)
    
    def get_latency(self):
        return round(sum(self.latencies), 4)
    
    def get_latency_ms(self):
        return round(self.get_latency() * 1000, 2)

    def load_auth_service(self):
        name = f'sp_{self.pid}'
        credential = persistence.get_credential(name=name)
        if not credential:
            credential = stirsetup.issue_cert(name=name, ctype='sp')
        self.auth_service = AuthService(
            ownerId=self.pid,
            private_key_pem=credential[constants.PRIV_KEY],
            x5u=config.CERT_REPO_BASE_URL + f'/certs/sp_{self.pid}'
        )
    
    async def originate(self, src: str = None, dst: str = None) -> Union[SIPSignal, TDMSignal]:
        src = misc.fake_number(1) if src is None else src
        dst = misc.fake_number(1) if dst is None else dst
        attest = random.choice(['A', 'B', 'C'])
        
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, cps={self.cps_fqdn}) ORIGINATES Call From src={src} to dst={dst} with attest={attest}')
        token = self.auth_service.create_passport(orig=src, dest=dst, attest=attest)
        signal = {'To': dst, 'From': src, 'Pid': self.pid}
        signal = SIPSignal(**signal, Identity=token)
        
        if not self.impl:
            signal: TDMSignal = await self.publish(sip_signal=signal)
            
        self.log_msg(f'--> Forwards {get_type(signal)}')
            
        return signal, token
    
    async def receive(self, incoming_signal: Union[SIPSignal, TDMSignal]) -> Union[SIPSignal, TDMSignal]:
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, cps={self.cps_fqdn}) RECEIVES {get_type(incoming_signal)}')

        outgoing_signal = None

        # If incoming signal is SIP then it must contain a token
        if isinstance(incoming_signal, SIPSignal):
            if not self.impl: # If converting to TDM then publish the token first
                outgoing_signal: TDMSignal = await self.publish(incoming_signal)
            else:
                # if no need to convert to TDM, then just forward the signal
                outgoing_signal = self.convert_sip_from_sip(incoming_signal)
        
        # If incoming signal is TDM then it must not contain a token
        if isinstance(incoming_signal, TDMSignal):
            if self.impl: # If converting to SIP then retrieve the token and convert
                outgoing_signal: SIPSignal = await self.retrieve(incoming_signal)
            else:
                # if no need to convert to SIP, then just forward the signal
                outgoing_signal = self.convert_tdm_from_tdm(incoming_signal)
        
        self.log_msg(f'--> Forwards {get_type(outgoing_signal)}')
        return outgoing_signal
    
    async def terminate(self, incoming_signal: Union[SIPSignal, TDMSignal]):
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, cps={self.cps_fqdn}) TERMINATES {get_type(incoming_signal)}')

        if isinstance(incoming_signal, SIPSignal):
            return incoming_signal.Identity
        
        # Incoming signal is TDM so let's retrieve
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
        url: str = self.cps_url + f'/publish/{signal.To}/{signal.From}'
        await http.posts(reqs=[{'url': url, 'data': payload, 'headers': headers}])
        
    async def cpex_publish(self, signal: SIPSignal):
        # Call ID generation
        call_id = await self.cpex_call_id_generation(signal=signal)
        # Encrypt and MAC, then sign the requests
        reqs = libcpex.create_storage_requests(
            call_id=call_id, 
            msg=signal.Identity,
            gsk=self.gsk,
            gpk=self.gpk
        )
        
        await http.posts(reqs=reqs)
    
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
        url: str = self.cps_url + f'/retrieve/{signal.To}/{signal.From}'
        response = await http.get(url=url, params={}, headers=headers)
        return response
    
    async def cpex_call_id_generation(self, signal: Union[SIPSignal, TDMSignal]) -> str:
        call_details: str = libcpex.normalize_call_details(src=signal.From, dst=signal.To)
        requests, masks = libcpex.create_evaluation_requests(call_details, gsk=self.gsk, gpk=self.gpk)
        responses = await http.posts(reqs=requests)
        return libcpex.create_call_id(responses=responses, masks=masks)

    async def cpex_retrieve_token(self, signal: TDMSignal) -> List[str]:
        call_id = await self.cpex_call_id_generation(signal=signal)
        reqs = libcpex.create_retrieve_requests(call_id=call_id, gsk=self.gsk, gpk=self.gpk)
        responses = await http.posts(reqs)
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
            'Identity': token
        })
    
    def convert_sip_from_sip(self, signal: SIPSignal) -> SIPSignal:
        if not isinstance(signal, SIPSignal):
            raise Exception('Signal must be an instance of SIPSignal class')
        
        return SIPSignal(**{
            'To': signal.To,
            'From': signal.From,
            'Pid': self.pid,
            'Identity': signal.Identity
        })
    
    def convert_tdm_from_tdm(self, signal: TDMSignal) -> TDMSignal:
        if not isinstance(signal, TDMSignal):
            raise Exception('Signal must be an instance of TDMSignal class')
        
        return TDMSignal(**{
            'To': signal.To,
            'From': signal.From,
            'Pid': self.pid
        })