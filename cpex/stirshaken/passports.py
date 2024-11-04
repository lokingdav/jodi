from uuid import uuid4
import time, jwt
import cpex.stirshaken.certs as certs
from typing import List, Annotated, Literal

from cpex.requests.validators.rules import (
    PhoneNumberValidator, 
    PassportTokenValidator, 
    AttestationValidator,
    AlgValidator,
    x5uValidator
)

from pydantic import BaseModel,  HttpUrl, Field

class TNModel(BaseModel):
    tn: PhoneNumberValidator

class PassportHeader(BaseModel):
    ppt: str = 'shaken'
    typ: str = 'passport'
    x5u: x5uValidator
    alg: AlgValidator  = 'ES256'

    def to_dict(self) -> dict:
        return self.model_dump()
        
    @staticmethod
    def from_dict(data: dict) -> 'PassportHeader':
        return PassportHeader(**data)
    
class PassportPayload(BaseModel):
    attest: AttestationValidator
    orig: TNModel
    dest: TNModel
    iat: int = int(time.time())
    origid: str = str(uuid4())
        
    def to_dict(self):
        return self.model_dump()

    @staticmethod
    def from_dict(data: dict):
        return PassportPayload(**data)

class Passport(BaseModel):
    header: PassportHeader
    payload: PassportPayload
    is_verified: bool = False
    jwt_token: PassportTokenValidator = None
        
    def get_orig_tn(self) -> str:
        return self.payload.orig.tn
    
    def get_dest_tn(self) -> str:
        return self.payload.dest.tn
    
    def get_tokens(self) -> List[str]:
        return [self.jwt_token]

    def sign(self, private_key: str) -> str:
        private_key = certs.get_private_key(private_key)
        
        self.payload.iat = int(time.time())
        self.payload.origid = str(uuid4())
        
        self.jwt_token = jwt.encode(
            payload=self.payload.to_dict(),
            key=private_key,
            algorithm=self.header.alg,
            headers=self.header.to_dict()
        )
        
        return self.jwt_token

    @staticmethod
    def verify_jwt_token(token: str, public_key: str, header: PassportHeader = None) -> 'Passport':
        header = PassportHeader(**jwt.get_unverified_header(token)) if not header else header
        decoded: PassportPayload = PassportPayload(**jwt.decode(token, public_key, algorithms=[header.alg]))
        return Passport(header=header, payload=decoded, jwt_token=token, is_verified=True)
