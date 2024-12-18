import jwt
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel
from cpex.helpers import misc

class AuthService(BaseModel):
    ownerId: str
    private_key_pem: str
    x5u: str
    
    def create_passport(self, orig: str, dest: str, attest: str) -> str: 
        header = { 'alg': 'ES256', 'x5u': self.x5u, 'ppt': 'shaken', 'typ': 'passport' }
        payload = { 
            'iat': int(datetime.timestamp()), 
            'attest': attest, 
            'orig': { 'tn': [orig] }, 
            'dest': { 'tn': [dest] } 
        }
        return self.create_jwt(
            header=header, 
            payload=payload, 
            private_key=self.private_key_pem
        )
    
    def authenticate_request(self, action: str, orig: str, dest: str, passports: list, iss: str, aud: str):
        header: dict = { 'alg': 'ES256',  'x5u': self.x5u }
        payload: dict = {
            'iat': int(datetime.timestamp()), 
            'action': action, 
            'passports': 'sha256-' + misc.base64encode(misc.hash256(passports)),
            'sub': iss, 
            'iss': iss, 
            'aud': aud, 
            'jti': str(uuid4()),
            'dest': { 'tn': [dest]},
            'orig': { 'tn': [orig]},
        }
        return self.create_jwt(
            header=header, 
            payload=payload, 
            private_key=self.private_key_pem
        )
        
    def create_jwt(self, header, payload, private_key) -> str:
        return jwt.encode(
            payload=payload,
            key=private_key,
            algorithm=header.alg,
            headers=header
        )
        