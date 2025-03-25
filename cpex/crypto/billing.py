from pylibcpex import Voprf, Utils
from cpex import config

def create_endorsed_token(sk: bytes):
    sk = Utils.from_base64(sk) if isinstance(sk, str) else sk
    t_0 = Utils.random_bytes(config.SEC_PARAM_BYTES)
    t_0 = Utils.to_base64(t_0)
    x, r = Voprf.blind(t_0)
    t_1 = Voprf.unblind(Voprf.evaluate(sk, x), r)
    return t_0 + '.' + Utils.to_base64(t_1)

def verify_token(vk: bytes, token: str):
    t_0, t_1 = token.split('.')
    vk = Utils.from_base64(vk) if isinstance(vk, str) else vk
    t_1 = Utils.from_base64(t_1) if isinstance(t_1, str) else t_1
    return Voprf.verify(vk, t_0, t_1)

def get_billing_hash(token: str, peers: str):
    return Utils.to_base64(Utils.hash256(bytes(token + peers, 'utf-8')))