import jwt, uuid
import validators, requests, time
from urllib.parse import quote, urlparse
from oobshaken.passports import Passport
import oobshaken.cert_repo as cr
import oobshaken.config as config
import oobshaken.helpers as helpers
from oobshaken.schema import Publish as PubForm

class CPSRequest:
    def __init__(self, issuer: str, cps_base_url: str, x5u: str):
        if not validators.url(cps_base_url) and not cps_base_url.startswith('http'):
            raise ValueError(f'CPS URL must be a valid url: {cps_base_url}')
        if not validators.url(x5u) and not x5u.startswith('http'):
            raise ValueError(f'CPS URL must be a valid url: {x5u}')
        self.cps_base_url: str = cps_base_url
        self.x5u: str = x5u
        self.issuer: str = issuer
        self.auth_token: str = None
        
    def authenticate(self, keypath: str) -> str:
        self.auth_token = jwt.encode(
            payload=self.get_auth_payload(),
            key=cr.get_private_key(keypath=keypath),
            algorithm=config.ALG,
            headers={'alg': config.ALG, 'x5u': self.x5u}
        )
        
    def get_headers(self) -> dict:
        headers = {
            'Content-Type': 'application/json',
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers
        
    def get_auth_payload(self) -> dict:
        return {
            'iat': int(time.time()),
            'aud': urlparse(self.cps_base_url).netloc,
            'iss': self.issuer,
            'sub': self.issuer,
            'jti': str(uuid.uuid4())
        }


class Publish(CPSRequest):
    def __init__(self, passport: Passport, issuer: str, cps_base_url: str, x5u: str):
        super().__init__(cps_base_url=cps_base_url, x5u=x5u, issuer=issuer)
        
        if not (passport.validate() and passport.is_signed()):
            raise ValueError('Passport must be signed before publishing')
        
        self.passport: Passport = passport
        orig: str = quote(passport.get_orig_tn(), safe='')
        dest: str = quote(passport.get_dest_tn(), safe='')
        self.url = f'{cps_base_url}/{dest}/{orig}'
        
    def submit(self, auth: bool = True) -> dict:
        if auth and not self.auth_token:
            raise ValueError('Call req.authorize() to authorize this request or set auth=False to skip authorization')
            
        res = requests.post(
            url=self.url, 
            json={'passports': self.passport.get_tokens()}, 
            headers=self.get_headers()
        )
        res.raise_for_status()
        
        return res.json()
    
    def get_auth_payload(self) -> dict:
        data: dict = super().get_auth_payload()
        data.update({
            'action': 'publish',
            'passports': 'sha256-' + helpers.base64encode(helpers.hash256(self.passport.get_tokens())),
            'orig': self.passport.payload.orig,
            'dest': self.passport.payload.dest
        })
        return data
    
    @staticmethod
    def validate_request(req: PubForm, orig: str, dest: str, auth_token: str) -> bool:
        try:
            # Verify the JWT token
            jwt_token = auth_token.split(' ')[-1]
            header: dict = jwt.get_unverified_header(jwt_token)
            public_key: str = cr.get_public_key_from_cert(header.get('x5u'))
            decoded = jwt.decode(
                jwt_token, 
                public_key, 
                algorithms=[header.get('alg')],
                audience=config.CPS_FQDN
            )
            # Verify the request
            required_fields = ['orig', 'dest', 'passports', 'action', 'iat', 'aud', 'iss', 'sub', 'jti']
            if not all([f in decoded for f in required_fields]):
                raise ValueError('Missing required fields')
            
            if decoded.get('action') != 'publish':
                raise ValueError('Invalid action')
            
            if 'tn' not in decoded.get('orig') or 'tn' not in decoded.get('dest'):
                raise ValueError('Invalid orig or dest format')
            
            if decoded['dest']['tn'] != dest or decoded['orig']['tn'] != orig:
                raise ValueError('Invalid orig or dest values')
            
            ppt: str = 'sha256-' + helpers.base64encode(helpers.hash256(req.passports))
            if ppt != decoded.get('passports'):
                raise ValueError('Invalid passports field')
            
            return True
        except Exception as e:
            print(e)
            return False
