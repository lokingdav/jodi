import random
from uuid import uuid4
from pydantic import BaseModel
from datetime import datetime
from cpex.config import CERT_REPO_BASE_URL, IS_ATIS_MODE, CPS_BASE_URL
from cpex.helpers import misc, http
from cpex.prototype.stirshaken.auth_service import AuthService

class SIPSignal(BaseModel):
    Pid: str
    To: str
    From: str
    CallId: str = str(uuid4())
    Identity: str

class TDMSignal(BaseModel):
    Pid: str
    To: str
    From: str

class Provider:
    impl: bool = False
    auth_service: AuthService
    cps_url: str
    cpc_urls: str
    gsp: dict
    
    def __init__(self, pid: str, impl: bool, priv_key_pem: str, cps_url: str, cpc_urls: list[str], gsp: dict):
        self.pid = pid
        self.impl = impl
        self.cps_url = cps_url
        self.cpc_urls = cpc_urls
        self.gsp = gsp
        
        self.auth_service = AuthService(
            private_key_pem=priv_key_pem,
            x5u=CERT_REPO_BASE_URL + f'/certs/{pid}'
        )
    
    def originate(self, src: str = None, dst: str = None) -> SIPSignal | TDMSignal:
        src = misc.fake_number() if src is None else src
        dst = misc.fake_number() if dst is None else dst
        attest = random.choice(['A', 'B', 'C'])
        
        print(f'-> Provider({self.pid}, imp={self.impl}) ORIGINATES Call From src={src} to dst={dst} with attest={attest}')
        token = self.auth_service.create_passport(orig=src, dest=dst, attest=attest)
        signal = {'To': dst, 'From': src, 'Pid': self.pid}
        signal = SIPSignal(**signal, Identity=token)
        
        if not self.impl:
            signal = self.publish(signal=signal)
            
        print('--> Forwards', type(signal))
            
        return signal, token
    
    def receive(self, signal: SIPSignal | TDMSignal) -> SIPSignal | TDMSignal:
        print(f'-> Provider({self.pid}, imp={self.impl}) RECEIVES call signal', type(signal))
        if isinstance(signal, SIPSignal) and not self.impl:
            signal = self.publish(signal)
        
        if isinstance(signal, TDMSignal) and self.impl:
            signal = self.retrieve(signal)
        
        signal.Pid = self.pid
        
        print('--> Forwards', type(signal))
        
        return signal
    
    def terminate(self, signal: SIPSignal | TDMSignal):
        print(f'-> Provider({self.pid}, imp={self.impl}) TERMINATES call signal', type(signal))
        if isinstance(signal, SIPSignal):
            return signal.Identity
        
        signal = self.retrieve(signal=signal)
        print('--> Call Terminated')
        return signal.Identity
        
    def publish(self, sip_signal: SIPSignal) -> TDMSignal:
        tdm_signal = self.convert_sip_to_tdm(signal=sip_signal)
        
        if not sip_signal.Identity:
            return tdm_signal
        
        print(f'--> Executes PUBLISH')
        
        if IS_ATIS_MODE:
            reqs = self.atis_publish(signal=sip_signal)
        else:
            reqs = self.cpex_publish(signal=sip_signal)
        
        http.multipost(reqs=reqs)
        
        return tdm_signal
        
    def atis_publish(self, signal: SIPSignal):
        authorization: str = self.auth_service.authenticate_request(
            tokens=[signal.Identity],
            cps_url=self.cps_url,
            action='publish'
        )
        return atis_oob.get_publish_requests(
            url=self.cps_url,
            token=signal.Identity, 
            authorization=authorization
        )
        
    def cpex_publish(self, signal: SIPSignal):
        ts: int = cpexlib.normalizeTs(int(datetime.timestamp()))
        label = cpexlib.get_label(src=signal.From, dst=signal.To, ts=ts)
        data, shares = cpexlib.secure(label=label, passport=signal.Identity)
        return cpexlib.get_publish_requests(
            cps_url=self.cps_url, 
            cpc_urls=self.cpc_urls,
            data=data,
            shares=shares
        )
    
    def retrieve(self, signal: TDMSignal) -> SIPSignal:
        print(f'--> Executes RETRIEVE')
        token = 'abc_123.XYZ-789.qwe_QWE'
        signal = self.convert_tdm_to_sip(signal=signal, token=token)
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
            'Identity': token
        })