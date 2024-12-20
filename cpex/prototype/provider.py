import random
from uuid import uuid4
from pydantic import BaseModel
from datetime import datetime
import cpex.config as config
import cpex.constants as constants
from cpex.helpers import misc, http
from cpex.prototype.stirshaken.auth_service import AuthService
from typing import List, Union
from cpex.crypto import libcpex
import aiohttp, asyncio
from cpex.models import persistence
from cpex.prototype.stirshaken import stirsetup

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
    def __init__(self, pid: str, impl: bool, cps_url: str):
        self.pid = pid
        self.impl = impl
        self.cps_url = cps_url
        self.session = aiohttp.ClientSession()
        self.load_auth_service()

    def __del__(self):
        self.session.close()

    def load_auth_service(self):
        name = f'vps_{self.pid}'
        credential = persistence.get_credential(name=name)
        if not credential:
            credential = stirsetup.issue_cert(name=name, ctype='vps')
        self.auth_service = AuthService(
            private_key_pem=credential[constants.PRIV_KEY],
            x5u=config.CERT_REPO_BASE_URL + f'/certs/{self.pid}'
        )
    
    async def originate(self, src: str = None, dst: str = None) -> Union[SIPSignal, TDMSignal]:
        src = misc.fake_number() if src is None else src
        dst = misc.fake_number() if dst is None else dst
        attest = random.choice(['A', 'B', 'C'])
        
        print(f'-> Provider({self.pid}, imp={self.impl}) ORIGINATES Call From src={src} to dst={dst} with attest={attest}')
        token = self.auth_service.create_passport(orig=src, dest=dst, attest=attest)
        signal = {'To': dst, 'From': src, 'Pid': self.pid}
        signal = SIPSignal(**signal, Identity=token)
        
        if not self.impl:
            signal: TDMSignal = await self.publish(signal=signal)
            
        print('--> Forwards', type(signal))
            
        return signal, token
    
    async def receive(self, incoming_signal: Union[SIPSignal, TDMSignal]) -> Union[SIPSignal, TDMSignal]:
        print(f'-> Provider({self.pid}, imp={self.impl}) RECEIVES call signal', type(incoming_signal))

        outgoing_signal = None

        # If incoming signal is SIP and converting to TDM? then publish first
        if isinstance(incoming_signal, SIPSignal) and not self.impl:
            outgoing_signal: TDMSignal = await self.publish(incoming_signal)
        
        # If incoming signal is TDM and converting to SIP, then retrieve
        if isinstance(incoming_signal, TDMSignal) and self.impl:
            outgoing_signal: SIPSignal = await self.retrieve(incoming_signal)
        
        outgoing_signal.Pid = self.pid
        print('--> Forwards', type(outgoing_signal))
        
        return outgoing_signal
    
    async def terminate(self, incoming_signal: Union[SIPSignal, TDMSignal]):
        print(f'-> Provider({self.pid}, imp={self.impl}) TERMINATES call signal', type(incoming_signal))

        if isinstance(incoming_signal, SIPSignal):
            return incoming_signal.Identity
        
        # Incoming signal is TDM so let's retrieve
        terminated_signal: SIPSignal = await self.retrieve(signal=incoming_signal)

        print('--> Call Terminated')
        return terminated_signal.Identity
        
    async def publish(self, sip_signal: SIPSignal) -> TDMSignal:
        tdm_signal = self.convert_sip_to_tdm(signal=sip_signal)
        
        if not sip_signal.Identity:
            return tdm_signal
        
        print(f'--> Executes PUBLISH')
        
        if config.IS_ATIS_MODE:
            await self.atis_publish(signal=sip_signal)
        else:
            await self.cpex_publish(signal=sip_signal)
        
        return tdm_signal
        
    async def atis_publish(self, signal: SIPSignal):
        authorization: str = self.auth_service.authenticate_request(
            action='publish',
            orig=signal.From,
            dest=signal.To,
            passports=[signal.Identity],
            iss=self.pid,
            aud=self.cps_url
        )
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        payload: dict = {'passports': [ signal.Identity ]}
        url: str = self.cps_url + f'/publish/{signal.From}/{signal.To}'
        await http.post(url=url, data=payload, headers=headers)
        
    async def cpex_publish(self, signal: SIPSignal):
        call_details: str = libcpex.get_call_details(src=signal.From, dst=signal.To)
        call_id = libcpex.generate_call_id(call_details)
        ctx = libcpex.encrypt_and_mac(call_id=call_id, msg=signal.Identity)
        reqs = libcpex.create_publish_requests(
            count=config.REPLICATION, 
            call_id=call_id, 
            ctx=ctx
        )
        await http.posts(reqs=reqs)
    
    async def retrieve(self, signal: TDMSignal) -> SIPSignal:
        print(f'--> Executes RETRIEVE')
        if config.IS_ATIS_MODE:
            tokens = await self.atis_retrieve_token(signal=signal)
        else:
            tokens = await self.cpex_retrieve_token(signal=signal)
        signal = self.convert_tdm_to_sip(signal=signal, token=tokens[0])
        return signal
    
    async def atis_retrieve_token(self, signal: TDMSignal) -> List[str]:
        authorization: str = self.auth_service.authenticate_request(
            action='retrieve',
            orig=signal.From,
            dest=signal.To,
            passports=[],
            iss=self.pid,
            aud=self.cps_url
        )
        headers: dict = {'Authorization': 'Bearer ' + authorization }
        url: str = self.cps_url + f'/retrieve/{signal.From}/{signal.To}'
        response = await http.get(url=url, params={}, headers=headers)
        return [response['token']]

    async def cpex_retrieve_token(self, signal: TDMSignal) -> List[str]:
        call_details: str = libcpex.get_call_details(src=signal.From, dst=signal.To)
        call_id = libcpex.generate_call_id(call_details)
        requests = libcpex.create_retrieve_requests(count=config.REPLICATION, call_id=call_id)
        responses = await http.post(requests)
        tokens = libcpex.decrypt(call_id, responses)
        return tokens
            
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