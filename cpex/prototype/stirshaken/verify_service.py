import jwt, traceback
from cpex.prototype.stirshaken import certs
from cpex.models import cache
from cpex import config
from cpex.helpers import mylogging

def load_public_key(x5u: str):
    key = f'{config.NODE_FQDN}:certs:{x5u}'
    certificate = cache.find(key)
    if not certificate:
        certificate = certs.download(x5u)
        if certificate:
            cache.save(key=key, value=certificate)
        else:
            return None
    certificate = certificate.replace("\\n", "\n")
    return certs.get_public_key_from_cert(certificate)

def verify_token(token: str, audience: str = config.NODE_FQDN) -> dict:
    header = jwt.get_unverified_header(token)
    public_key = load_public_key(header['x5u'])
    mylogging.mylogger.debug(f"Public Key: {public_key}")
    if not public_key:
        return None
    try:
        return jwt.decode(token, public_key, algorithms=[header['alg']], audience=audience)
    except Exception as e:
        mylogging.mylogger.error(f'Error verifying token: {e}')
        return None
