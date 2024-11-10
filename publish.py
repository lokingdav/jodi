import random
from cpex.providers.provider import Provider
from cpex.helpers import files
from cpex.config import CONF_DIR, INITIAL_CPS_NODES

pid: str = 'vsp_0'
impl: bool = False
keys: dict = files.read_json(CONF_DIR + '/vps.sks.json')

if __name__ == '__main__':
    provider = Provider(
        pid=pid, 
        impl=impl, 
        priv_key_pem=keys[pid],
        cps_id=random.randint(0, INITIAL_CPS_NODES)
    )
    
    signal, token = provider.originate()
    print('Signal:', type(signal))
    print('Token:', token)