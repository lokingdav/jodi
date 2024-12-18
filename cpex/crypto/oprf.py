from pylibcpex import Oprf, KeyRotation, Utils
from cpex import config

def evaluate(privk: bytes, publk: bytes, x: str) -> dict:
    fx, vk = Oprf.evaluate(privk, publk, Utils.from_base64(x))
    return { "fx": Utils.to_base64(fx), "vk": Utils.to_base64(vk) }

def begin_key_rotation():
    instance = KeyRotation.get_instance()
    instance.start_rotation(
        config.OPRF_KEYLIST_SIZE,
        config.OPRF_INTERVAL_SECONDS
    )
    return instance

def stop_key_rotation(instance):
    instance.stop_rotation()