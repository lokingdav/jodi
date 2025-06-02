import random, traceback, time, json
from uuid import uuid4
from pydantic import BaseModel
import jodi.config as config
from jodi.helpers import misc
from typing import Union
from jodi.models.iwf import JodiIWF
from jodi.prototype.stirshaken.oobss_iwf import OobSSIWF

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

class Provider(JodiIWF, OobSSIWF):
    def __init__(self, params: dict):
        JodiIWF.__init__(self, params)
        OobSSIWF.__init__(self, params)
        
        self.latencies = []
        self.mode = params['mode']
        self.impl = params['impl']
        self.next_prov = params.get('next_prov')

    def is_oobss_mode(self):
        return config.is_oobss_mode(self.mode)
    
    def get_latency(self):
        return sum(self.latencies) - sum(self.sim_overhead)
    
    def get_latency_ms(self):
        return self.get_latency() * 1000
    
    def next_prov_is_capable(self):
        return self.next_prov and self.next_prov[1] == 1
    
    def reset(self):
        self.latencies = []
        super().reset()
    
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
        
        if self.is_oobss_mode():
            await self.oobss_publish_token(
                src=sip_signal.From, 
                dst=sip_signal.To, 
                identity=sip_signal.Identity
            )
        else:
            await self.jodi_publish(
                src=sip_signal.From, 
                dst=sip_signal.To, 
                token=sip_signal.Identity
            )
            
        time_taken = time.perf_counter() - start_time
        self.latencies.append(time_taken)
        self.publish_provider_time += time_taken
        return tdm_signal
    
    async def retrieve(self, signal: TDMSignal) -> SIPSignal:
        self.log_msg(f'--> Executes RETRIEVE')
        try: 
            start_time = time.perf_counter()
            if self.is_oobss_mode():
                token = await self.oobss_retrieve_token(src=signal.From, dst=signal.To)
            else:
                token = await self.jodi_retrieve(src=signal.From, dst=signal.To)
                
            time_taken = time.perf_counter() - start_time
            self.latencies.append(time_taken)
            self.retrieve_provider_time += time_taken
            
            signal = self.convert_tdm_to_sip(signal=signal, token=token)
        except Exception as e:
            self.log_msg(f'Error while executing RETRIEVE: {e}')
            traceback.print_exc()
            signal = self.convert_tdm_to_sip(signal=signal)
        return signal

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