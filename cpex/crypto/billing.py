from pylibcpex import Voprf, Utils
from cpex import config

def create_endorsed_token(sk: bytes):
    sk = Utils.from_base64(sk) if isinstance(sk, str) else sk
    p, x, r = Voprf.blind(Utils.to_base64(Utils.random_bytes(32)))
    fx = Voprf.evaluate(sk, x)
    y = Voprf.unblind(fx, r)
    return Utils.to_base64(p) + '.' + Utils.to_base64(y)

def verify_token(vk: bytes, token: str):
    p, y = token.split('.')
    vk = Utils.from_base64(vk) if isinstance(vk, str) else vk
    p = Utils.from_base64(p) if isinstance(p, str) else p
    y = Utils.from_base64(y) if isinstance(y, str) else y
    return Voprf.verify(vk, p, y)

def get_billing_hash(token: str, peers: str):
    return Utils.to_base64(Utils.hash256(bytes(token + peers, 'utf-8')))