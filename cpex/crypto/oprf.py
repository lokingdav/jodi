from pylibcpex import Oprf, Utils
from cpex import config
from cpex.models import cache
import time
from typing import Tuple

def evaluate(sk: bytes, pk: bytes, x: str) -> dict:
    fx, vk = Oprf.evaluate(sk, pk, Utils.from_base64(x))
    return { "fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk) }

class KeyRotation:
    @staticmethod
    def get_key(i: int) -> Tuple[bytes, bytes]:
        if i < 0 or i >= config.KEYLIST_SIZE:
            raise ValueError('Index out of bounds')
        sk, pk = cache.find(key=KeyRotation.get_record_label(i)).split('.')
        return Utils.from_base64(sk), Utils.from_base64(pk)

    @staticmethod
    def get_record_label(i: int) -> str:
        return f'{config.KEY_ROTATION_LABEL}.{i}'
    
    @staticmethod
    def initialize_keys():
        for i in range(config.KEYLIST_SIZE):
            KeyRotation.renew_key(i)

    @staticmethod
    def renew_key(index: int):
        sk, pk = Oprf.keygen()
        cache.save(
            key=KeyRotation.get_record_label(index), 
            value=f'{Utils.to_base64(sk)}.{Utils.to_base64(pk)}'
        )
    
    @staticmethod
    def save_recently_expired(exp_idx: int):
        keypair = cache.find(key=KeyRotation.get_record_label(exp_idx))
        cache.cache_for_seconds(
            key=f'{config.KEY_ROTATION_LABEL}.recently_expired',
            value=keypair,
            seconds=config.LIVENESS_WINDOW_SECONDS
        )

    @staticmethod
    def begin_rotation():
        exp_idx = -1
        while True:
            time.sleep(config.ROTATION_INTERVAL_SECONDS)
            print(f"Rotating key at index {exp_idx}", flush=True)
            exp_idx = (exp_idx + 1) % config.KEYLIST_SIZE
            KeyRotation.save_recently_expired(exp_idx)
            KeyRotation.renew_key(exp_idx)
            