import jwt

from cpex.prototype.stirshaken.passports import PassportHeader, Passport
from cpex.requests.validators.rules import x5uValidator
from cpex.prototype.stirshaken import certs
from cpex.models import cache

class VerifyService:
    def load_public_key(self, x5u: str):
        cert_key = x5u.split('/')[-1]
        
        certificate = cache.find(key=cert_key)
        
        if not certificate:
            certificate = certs.download(x5u)
            cache.save(key=cert_key, value=certificate)
        
        return certs.get_public_key_from_cert(certificate)
        
    def verify_passport(self, token: str) -> str: 
        passport: Passport = None
        try:
            header = PassportHeader(**jwt.get_unverified_header(token))
            public_key = self.load_public_key(header.x5u)
            passport = Passport.verify_jwt_token(
                token, 
                public_key=public_key,
                header=header
            )
        except:
            return False

        return passport is not None
    
        