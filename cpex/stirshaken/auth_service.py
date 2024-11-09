from pydantic import BaseModel
from cpex.stirshaken.passports import PassportHeader, PassportPayload, Passport, TNModel
from cpex.requests.validators.rules import x5uValidator

class AuthService(BaseModel):
    private_key_pem: str
    x5u: x5uValidator
    
    def authenticate(self, orig: str, dest: str, attest: str) -> str: 
        header = PassportHeader(x5u=self.x5u)
        payload = PassportPayload(attest=attest, orig=TNModel(tn=orig), dest=TNModel(tn=dest))
        passport = Passport(header=header, payload=payload)
        return passport.sign(private_key=self.private_key_pem)
        