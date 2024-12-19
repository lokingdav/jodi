import jwt
from cpex.prototype.stirshaken import certs
from cpex.models import cache

def load_public_key(x5u: str):
    cert_key = x5u.split('/')[-1]
    certificate = cache.find(key=cert_key)
    if not certificate:
        certificate = certs.download(x5u)
        cache.save(key=cert_key, value=certificate)
    return certs.get_public_key_from_cert(certificate)

def verify_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    public_key = load_public_key(header['x5u'])
    try:
        return jwt.decode(token, public_key, algorithms=[header['alg']])
    except:
        return None
