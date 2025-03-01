import jwt, traceback
from cpex.prototype.stirshaken import certs
from cpex.models import cache
from cpex import config
from cpex.helpers import mylogging

def load_public_key(x5u: str):
    if config.USE_LOCAL_CERT_REPO:
        key = x5u.split('/')[-1]
        certificate = cache.find(key)
    else:
        certificate = cache.find(x5u)
        if not certificate:
            certificate = certs.download(x5u)
            if certificate:
                try:
                    certs.verify_chain_of_trust(certificate.replace("\\n", "\n"))
                except Exception as e:
                    mylogging.mylogger.error(f'Error verifying certificate {x5u}: {e}')
                    return None
                cache.cache_for_seconds(key=x5u, value=certificate, seconds=5)
            else:
                return None
        
    certificate = certificate.replace("\\n", "\n")
    
    return certs.get_public_key_from_cert(certificate)

def verify_token(token: str, audience: str = config.NODE_FQDN) -> dict:
    # return jwt.decode(token, options={"verify_signature": False})
    header = jwt.get_unverified_header(token)
    public_key = load_public_key(header['x5u'])
    # mylogging.mylogger.debug(f"Public Key: {public_key}")
    if not public_key:
        return None
    try:
        return jwt.decode(token, public_key, algorithms=[header['alg']], audience=audience)
    except Exception as e:
        # mylogging.mylogger.error(f'Error verifying token: {e}')
        return None
