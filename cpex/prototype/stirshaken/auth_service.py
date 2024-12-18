import jwt
from datetime import datetime
from pydantic import BaseModel
from cpex.helpers import misc
from cpex.stirshaken.passports import PassportHeader, PassportPayload, Passport, TNModel
from cpex.requests.validators.rules import x5uValidator

class AuthService(BaseModel):
    pid: str
    private_key_pem: str
    x5u: x5uValidator
    
    def create_passport(self, orig: str, dest: str, attest: str) -> str: 
        header = PassportHeader(x5u=self.x5u)
        payload = PassportPayload(attest=attest, orig=TNModel(tn=orig), dest=TNModel(tn=dest))
        passport = Passport(header=header, payload=payload)
        return passport.sign(private_key=self.private_key_pem)
    
    def authenticate_request(self, tokens: list, action: str, cps_id: str):
        header: dict = { 'alg': 'ES256',  'x5u': self.x5u }
        payload: dict = {
            'iat': int(datetime.timestamp()), 'aud': str(cps_id), 'iss': self.pid, 
            'sub': self.pid, 'action': action, 'passports': 'sha256-' + misc.base64encode(misc.hash256(tokens))
        }
        return jwt.encode(
            payload=payload,
            key=self.private_key_pem,
            algorithm=header['alg'],
            headers=header
        )
        