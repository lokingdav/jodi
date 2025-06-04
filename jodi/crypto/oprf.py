from pylibjodi import Voprf, Utils
from jodi import config
from jodi.models import cache
import time
from typing import Tuple
from jodi.crypto import audit_logging

EXP_PREFIX = 'rexp'

def evaluate(keypairs: list, x: str, isk) -> dict:
    evaluations = []
    for (sk, vk) in keypairs:
        fx = Voprf.evaluate(sk, Utils.from_base64(x))
        evaluations.append({ "fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk) })
    sigma: str = audit_logging.ecdsa_sign(private_key=isk, data=evaluations)
    return {"evals": evaluations, "sig": sigma}

class KeyRotation:
    @staticmethod
    def get_keys(i: int) -> Tuple[bytes, bytes]:
        if i < 0 or i >= config.KEYLIST_SIZE:
            raise ValueError('Index out of bounds')
        
        rkeys = [KeyRotation.get_record_label(i), KeyRotation.get_record_label(f'{EXP_PREFIX}.{i}')]
        items = cache.find_all(rkeys)
        
        keypairs = []
        for item in items:
            if not item:
                continue
            
            sk, pk = item.split('.')
            keypairs.append((Utils.from_base64(sk), Utils.from_base64(pk)))
        
        return keypairs

    @staticmethod
    def get_record_label(suffix: str) -> str:
        return f'{config.KEY_ROTATION_LABEL}.{suffix}'
    
    @staticmethod
    def initialize_keys():
        for i in range(config.KEYLIST_SIZE):
            KeyRotation.renew_key(i)

    @staticmethod
    def renew_key(index: int):
        sk, pk = Voprf.keygen()
        cache.save(
            key=KeyRotation.get_record_label(index), 
            value=f'{Utils.to_base64(sk)}.{Utils.to_base64(pk)}'
        )
    
    @staticmethod
    def save_recently_expired(exp_idx: int):
        keypair = cache.find(key=KeyRotation.get_record_label(exp_idx))
        cache.cache_for_seconds(
            key=KeyRotation.get_record_label(f'{EXP_PREFIX}.{exp_idx}'),
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
            