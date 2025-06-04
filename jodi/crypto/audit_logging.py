import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

from jodi.helpers import misc

def ecdsa_sign(private_key, data) -> str:
    if isinstance(private_key, str):
        private_key = serialization.load_pem_private_key(private_key.encode(), password=None)
    if isinstance(data, dict) or isinstance(data, list):
        data = misc.stringify(data)
    signature = private_key.sign(
        data.encode('utf-8'),
        ec.ECDSA(hashes.SHA256())
    )
    return base64.b64encode(signature).decode('utf-8')

def ecdsa_verify(public_key, data, sigma: str) -> bool:
    if isinstance(public_key, str):
        public_key = serialization.load_pem_public_key(public_key.encode())
    if isinstance(data, dict) or isinstance(data, list):
        data = misc.stringify(data)
        
    signature = base64.b64decode(sigma.encode('utf-8'))
    try:
        public_key.verify(
            signature,
            data.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False
