import jwt, traceback
from jodi.prototype.stirshaken import certs
from jodi.models import cache
from jodi import config
from jodi.helpers import mylogging

async def load_public_key(x5u: str):
    if config.USE_LOCAL_CERT_REPO:
        key = x5u.split('/')[-1]
        certificate = cache.find(key)
    else:
        certificate = cache.find(x5u)
        if not certificate:
            print("Downloading certificate from x5u:", x5u, flush=True)
            certificate = await certs.download(x5u)
            if certificate:
                try:
                    certs.verify_chain_of_trust(certificate.replace("\\n", "\n"))
                except Exception as e:
                    mylogging.mylogger.error(f'Error verifying certificate {x5u}: {e}')
                    return None
                cache.cache_for_seconds(key=x5u, value=certificate, seconds=10)
            else:
                return None
        
    certificate = certificate.replace("\\n", "\n")
    
    return certs.get_public_key_from_cert(certificate)

async def verify_token(token: str, audience: str = config.NODE_FQDN) -> dict:
    # return jwt.decode(token, options={"verify_signature": False})
    header = jwt.get_unverified_header(token)
    public_key = await load_public_key(header['x5u'])
    # mylogging.mylogger.debug(f"Public Key: {public_key}, Audience: {audience}")
    if not public_key:
        return None
    try:
        return jwt.decode(token, public_key, algorithms=[header['alg']], audience=audience)
    except Exception as e:
        mylogging.mylogger.error(f'Error verifying token: {e}')
        return None
