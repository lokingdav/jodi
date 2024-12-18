from argparse import ArgumentParser
from cpex.prototype.stirshaken import certs as sti_certs, auth_service as AS, verify_service as VS
from cpex.helpers import files, misc
from cpex.config import CONF_DIR
from cpex.constants import CERT_KEY, PRIV_KEY

conf = []

def register_provider(pid: str):
    certs_file = CONF_DIR + f'/vsp.{pid}.certs.json'
    keys = files.read_json(certs_file)
    
    if not keys:
        sk, csr = sti_certs.client_keygen(name=f'vsp_{pid}')
        cert = sti_certs.request_cert(csr)
        keys = { CERT_KEY: cert, PRIV_KEY: sk }
        files.override_json(fileloc=certs_file, data=keys)
    
    return keys

def get_call_path(path: str):
    if not path.isdigit() or set(path) > {'0', '1'}:
        raise Exception('Invalid format string for call path: Accepted values are binary digits')
    return [bool(d) for d in path]

def main(path: str):
    call_path = get_call_path(path)
    src, dst = misc.fake_number(), misc.fake_number("1")
    
    for i, shaken_aware in enumerate(call_path):
        if i == 0:
            pass

if __name__ == '__main__':
    parser = ArgumentParser(prog="Basic Simulation", description="Run basic simulation for CPeX")
    parser.add_argument("path", help="Call path to simulate. Must be a binary number e.g 00000. 1 represents implemented SHAKEN while 0 means otherwise")
    args = parser.parse_args()
    main(args.path)