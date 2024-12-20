import jwt, traceback
from cpex.prototype.stirshaken import certs
from cpex.models import cache
from cpex import config

def load_public_key(x5u: str):
    cert_key = 'certs.' + x5u.split('/')[-1]
    certificate = cache.find(cert_key)
    if not certificate:
        certificate = certs.download(x5u)
        if certificate:
            cache.save(key=cert_key, value=certificate)
        else:
            return None
    certificate = certificate.replace("\\n", "\n")
    return certs.get_public_key_from_cert(certificate)

def verify_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    public_key = load_public_key(header['x5u'])
    if not public_key:
        return None
    try:
        return jwt.decode(token, public_key, algorithms=[header['alg']], audience=config.REPO_FQDN)
    except Exception as e:
        print(f'Error verifying token: {e}')
        return None
