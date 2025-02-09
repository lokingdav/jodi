import jwt, traceback
from cpex.prototype.stirshaken import certs
from cpex.models import cache
from cpex import config

def load_public_key(x5u: str):
    certificate = cache.find(x5u)
    if not certificate:
        certificate = certs.download(x5u)
        if certificate:
            cache.save(key=x5u, value=certificate)
        else:
            return None
    certificate = certificate.replace("\\n", "\n")
    return certs.get_public_key_from_cert(certificate)

def verify_token(token: str, audience: str = config.NODE_FQDN) -> dict:
    header = jwt.get_unverified_header(token)
    public_key = load_public_key(header['x5u'])
    if not public_key:
        return None
    try:
        return jwt.decode(token, public_key, algorithms=[header['alg']], audience=audience)
    except Exception as e:
        print(f'Error verifying token: {e}')
        return None
