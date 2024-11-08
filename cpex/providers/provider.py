import random
from uuid import uuid4
from pydantic import BaseModel
from datetime import datetime
from cpex.config import CERT_REPO_BASE_URL
from cpex.helpers import misc
from cpex.requests.validators.rules import SipAddress, PassportTokenValidator
from cpex.stirshaken.auth_service import AuthService

class InviteMsg(BaseModel):
    To: SipAddress
    From: SipAddress
    CallId: str = str(uuid4())
    identity: PassportTokenValidator

class Provider:
    impl: bool = False
    auth_service: AuthService
    
    def __init__(self, pid: str, impl: bool, priv_key_pem: str):
        self.pid = pid
        self.impl = impl
        
        self.auth_service = AuthService(
            private_key_pem=priv_key_pem,
            x5u=CERT_REPO_BASE_URL + f'/certs/{pid}'
        )
    
    def originate(self, next_vsp: str, src: str = None, dst: str = None):
        src = misc.fake_number() if src is None else src
        dst = misc.fake_number() if dst is None else dst
        attest = random.choice(['A', 'B', 'C'])
        token = self.auth_service.authenticate(orig=src, dest=dst, attest=attest)
        return InviteMsg({'To': dst, 'From': src, 'Identity': token})
    
    def receive(invite: InviteMsg):
        pass