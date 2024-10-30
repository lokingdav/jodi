from uuid import uuid4
import time, validators, jwt
import oobshaken.cert_repo as cr
import oobshaken.config as config
from typing import List

class PassportHeader:
    def __init__(self, x5u: str, alg: str = config.ALG):
        self.alg: str = alg
        self.x5u: str = x5u
        self.ppt: str = 'shaken'
        self.typ: str = 'passport'
        
    def validate(self):
        if not validators.url(self.x5u) and not self.x5u.startswith('http'):
            raise ValueError(f'x5u must be a valid URL: {self.x5u}')

    def to_dict(self) -> dict:
        return { 'alg': self.alg, 'x5u': self.x5u, 'typ': self.typ, 'ppt': self.ppt}
        
    @staticmethod
    def from_dict(data: dict) -> 'PassportHeader':
        header = PassportHeader()
        header.alg = data.get('alg')
        header.x5u = data.get('x5u')
        header.typ = data.get('typ')
        header.ppt = data.get('ppt')
        return header
    
class PassportPayload:
    def __init__(self, attest: str, dest: dict, orig: dict, iat: int = None, origid: str = None):
        self.attest: str = attest
        self.dest: dict = dest
        self.orig: dict = orig
        self.iat: int = iat or int(time.time())
        self.origid: str = origid or str(uuid4())
        
    def validate(self):
        if self.attest not in ['A', 'B', 'C']:
            raise ValueError(f'Invalid attest value: {self.attest}')
        if 'tn' not in self.dest:
            raise ValueError(f'Destination missing tn field: {self.dest}')
        if 'tn' not in self.orig:
            raise ValueError(f'Originator missing tn field: {self.orig}')
        
    def to_dict(self):
        return { 
            'attest': self.attest, 
            'dest': self.dest, 
            'iat': self.iat, 
            'orig': self.orig, 
            'origid': self.origid
        }

    @staticmethod
    def from_dict(data: dict):
        payload = PassportPayload()
        payload.attest = data.get('attest')
        payload.dest = data.get('dest')
        payload.iat = data.get('iat')
        payload.orig = data.get('orig')
        payload.origid = data.get('origid')
        return payload

class Passport:
    def __init__(self, header: PassportHeader = None, payload: PassportPayload = None, jwt_token: str = None):
        self.header: PassportHeader = header
        self.payload: PassportPayload = payload
        self.jwt_token: str = None
        
    def validate(self):
        self.header.validate()
        self.payload.validate()
        return True
        
    def is_signed(self) -> bool:
        return self.jwt_token is not None
        
    def get_orig_tn(self) -> str:
        return self.payload.orig.get('tn')
    
    def get_dest_tn(self) -> str:
        return self.payload.dest.get('tn')
    
    def get_tokens(self) -> List[str]:
        return [self.jwt_token]

    def sign(self, keypath: str = None, key: str = None) -> 'Passport':
        key = cr.get_private_key(keypath=keypath, key=key)
        self.header.validate()
        self.payload.validate()
        self.jwt_token = jwt.encode(
            payload=self.payload.to_dict(),
            key=key,
            algorithm=self.header.alg,
            headers=self.header.to_dict()
        )
        return self

    @staticmethod
    def verify(token: str):
        header: dict = jwt.get_unverified_header(token)
        public_key: str = cr.get_public_key_from_cert(header.get('x5u'))
        decoded = jwt.decode(token, public_key, algorithms=[header.get('alg')])
        return decoded
    
    @staticmethod
    def from_jwt(token: str) -> 'Passport':
        header: dict = jwt.get_unverified_header(token)
        payload: dict = jwt.decode(token, verify=False)
        return Passport(
            header=PassportHeader.from_dict(header),
            payload=PassportPayload.from_dict(payload),
            jwt_token=token
        )
