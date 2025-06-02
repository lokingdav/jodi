from jodi.crypto.oprf import KeyRotation
from jodi.models import cache

cache.set_client(cache.connect())

def main():
    KeyRotation.initialize_keys()
    KeyRotation.begin_rotation()

if __name__ == '__main__':
    main()