from uuid import uuid4
from cryptography import x509
import validators, requests, traceback
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def get_certificate(url: str) -> x509.Certificate:
    if not validators.url(url) and not url.startswith('http'):
            raise ValueError(f'Cert url must be a valid URL: {url}')
    try:
        cert_str: str = requests.get(url=url).json()
        cert = x509.load_pem_x509_certificate(cert_str.encode(), default_backend())
        return cert
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f'Error getting certificate: {e}')
    
    
def get_public_key_from_cert(url: str) -> str:
        try:
            cert: x509.Certificate = get_certificate(url)
            public_key = cert.public_key()
            pem_public_key = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem_public_key.decode()
        except Exception as e:
            traceback.print_exc()
            raise ValueError(f'Error getting certificate: {e}')
        
def get_private_key(keypath: str = None, key: str = None):
    if not key and not keypath:
        raise ValueError('Must provide either a key or a keypath')
    if keypath:
        with open(keypath, 'rb') as f:
            key = f.read()
    if not key:
        raise ValueError('Invalid key or keypath')
    return key