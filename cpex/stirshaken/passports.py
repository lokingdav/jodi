from uuid import uuid4
import time, jwt
import cpex.stirshaken.certs as certs
from typing import List, Annotated, Literal
from cpex.requests.validators.rules import PhoneNumberValidator, PassportTokenValidator

from pydantic import BaseModel,  HttpUrl, Field

class TNModel(BaseModel):
    tn: PhoneNumberValidator

class PassportHeader(BaseModel):
    ppt: str = 'shaken'
    typ: str = 'passport'
    x5u: Annotated[str, HttpUrl]
    alg: Literal['RS256', 'ES256'] = 'ES256'

    def to_dict(self) -> dict:
        return self.model_dump()
        
    @staticmethod
    def from_dict(data: dict) -> 'PassportHeader':
        return PassportHeader(**data)
    
class PassportPayload(BaseModel):
    attest: Literal['A', 'B', 'C']
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

    def sign(self, key: str) -> 'Passport':
        key = certs.get_private_key(key)
        self.jwt_token = jwt.encode(
            payload=self.payload.to_dict(),
            key=key,
            algorithm=self.header.alg,
            headers=self.header.to_dict()
        )
        return self

    @staticmethod
    def verify_jwt_token(token: str) -> 'Passport':
        header: PassportHeader = PassportHeader(**jwt.get_unverified_header(token))
        public_key: str = certs.get_public_key_from_cert(header.x5u)
        decoded: PassportPayload = PassportPayload(**jwt.decode(token, public_key, algorithms=[header.alg]))
        return Passport(header=header, payload=decoded, jwt_token=token, is_verified=True)

