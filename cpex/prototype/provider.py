import random, traceback, time, json
from uuid import uuid4
from pydantic import BaseModel
import cpex.config as config
import cpex.constants as constants
from cpex.helpers import misc, http
from cpex.prototype.stirshaken.auth_service import AuthService
from typing import List, Union
from cpex.models import cache, iwf
from cpex.prototype.stirshaken import stirsetup

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

class Provider(iwf.CpexIWF):
    def __init__(self, params: dict):
        super().__init__(params)
        self.latencies = []
        self.mode = params['mode']
        self.pid = params['pid']
        self.SPC = f'sp_{self.pid}'
        self.impl = params['impl']
        self.next_prov = params.get('next_prov')

        self.cps = params.get('cps')
        self.cr = params.get('cr')

        if self.mode not in [constants.MODE_ATIS, constants.MODE_CPEX]:
            raise Exception('Mode must be specified as either atis or cpex')
        
        if config.is_atis_mode(self.mode):
            if not self.cps:
                raise Exception('CPS must be specified')
            if not self.cr:
                raise Exception('CR must be specified')
            
        self.load_auth_service()
    
    def is_atis_mode(self):
        return config.is_atis_mode(self.mode)
    
    def get_latency(self):
        return sum(self.latencies) - sum(self.sim_overhead)
    
    def get_latency_ms(self):
        return self.get_latency() * 1000
    
    def next_prov_is_capable(self):
        return self.next_prov and self.next_prov[1] == 1
    
    def reset(self):
        self.latencies = []
        super().reset()

    def load_auth_service(self):
        self.auth_service = AuthService(
            ownerId=self.pid,
            private_key_pem=self.cr['sk'],
            x5u=self.cr['x5u'],
        )
    
    async def originate(self, src: str = None, dst: str = None) -> Union[SIPSignal, TDMSignal]:
        src = misc.fake_number(1) if src is None else src
        dst = misc.fake_number(1) if dst is None else dst
        attest = random.choice(['A', 'B', 'C'])
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, ORIGINATES Call From src={src} to dst={dst} with attest={attest}')
        token = self.auth_service.create_passport(orig=src, dest=dst, attest=attest)
        signal = {'To': dst, 'From': src, 'Pid': self.pid}
        signal = SIPSignal(**signal, Identity=token)
        signal = await self.forward_call(signal)
        return signal, token
    
    async def forward_call(self, signal: Union[SIPSignal, TDMSignal]):
        if not self.impl or not self.next_prov_is_capable():
            signal: TDMSignal = await self.publish(sip_signal=signal)
        self.log_msg(f'--> FORWARDS {get_type(signal)} to {self.next_prov}')
        return signal
    
    async def receive(self, incoming_signal: Union[SIPSignal, TDMSignal]) -> Union[SIPSignal, TDMSignal]:
        self.log_msg(f'* Provider({self.pid}, imp={self.impl}, RECEIVES {get_type(incoming_signal)}')
        
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
        self.log_msg(f'* Provider({self.pid}, imp={self.impl} TERMINATES {get_type(incoming_signal)}')

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
            await self.cpex_publish(src=sip_signal.From, dst=sip_signal.To, token=sip_signal.Identity)
            
        time_taken = time.perf_counter() - start_time
        self.latencies.append(time_taken)
        self.publish_provider_time += time_taken
        return tdm_signal
        
    async def atis_publish(self, signal: SIPSignal):
        self.log_msg(f'--> Executes ATIS PUBLISH')
        authorization: str = self.auth_service.authenticate_request(
            action='publish',
            orig=signal.From,
            dest=signal.To,
            passports=[signal.Identity],
            iss=self.pid,
            aud=self.cps['fqdn']
        )
        # self.log_msg(f'Authorized Request with: Bearer {authorization}')
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        payload: dict = {'passports': [ signal.Identity ]}
        url: str = self.cps['url']
        url = f'{url}/publish/{signal.To}/{signal.From}'
        self.log_msg(f'--> PUBLISH URL: {url}')
        responses = await http.posts(reqs=[{'url': url, 'data': payload, 'headers': headers}])
        print("ATIS PUBLISH Responses: ", responses)
    
    async def retrieve(self, signal: TDMSignal) -> SIPSignal:
        self.log_msg(f'--> Executes RETRIEVE')
        try: 
            start_time = time.perf_counter()
            if self.is_atis_mode():
                token = await self.atis_retrieve_token(signal=signal)
            else:
                token = await self.cpex_retrieve(src=signal.From, dst=signal.To)
                
            time_taken = time.perf_counter() - start_time
            self.latencies.append(time_taken)
            self.retrieve_provider_time += time_taken
            
            signal = self.convert_tdm_to_sip(signal=signal, token=token)
        except Exception as e:
            self.log_msg(f'Error while executing RETRIEVE: {e}')
            traceback.print_exc()
            signal = self.convert_tdm_to_sip(signal=signal)
        return signal
    
    async def atis_retrieve_token(self, signal: TDMSignal) -> List[str]:
        self.log_msg(f'--> Executes ATIS RETRIEVE')
        authorization: str = self.auth_service.authenticate_request(
            action='retrieve',
            orig=signal.From,
            dest=signal.To,
            passports=[],
            iss=self.pid,
            aud=self.cps['fqdn']
        )
        # self.log_msg(f'Authorized Request with: Bearer {authorization}')
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        url: str = self.cps['url']
        url = f'{url}/retrieve/{signal.To}/{signal.From}'
        print(f'--> RETRIEVE URL: {url}')
        response = await http.get(url=url, params={}, headers=headers)
        print("ATIS RETRIEVE Response: ", response)
        if type(response) == list and len(response) > 0:
            return response[0]
        return response

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
            'Identity': token if token and type(token) == str else config.EMPTY_TOKEN
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