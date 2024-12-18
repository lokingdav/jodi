import random
from multiprocessing import Pool, Manager
from cpex.providers import network
from cpex.models import persistence
from cpex.helpers import errors, files
from cpex.prototype.stirshaken import certs
from cpex import config, constants
from cpex.providers.provider import Provider

processes = 4
vsp_priv_keys = {}
keyfile = config.CONF_DIR + '/vps.sks.json'

def load_private_keys():
    global vsp_priv_keys
    vsp_priv_keys = files.read_json(keyfile)

def simulate_call(entry: dict):
    route = entry.get('route', [])
    print('CALL ROUTE:', route)
    
    if len(route) == 0:
        raise Exception('Invalid simulation parameter')
    
    if not isinstance(route, list):
        raise Exception("Route parameter must be an instance of a list")
    
    if len(set([p for (p, _) in route])) == 1:
        return entry.get('_id')
        
    providers, signal, start_token, final_token = {}, None, None, None
    
    for i, (idx, impl) in enumerate(route):
        pid = 'vsp_' + str(idx)
        provider: Provider = providers.get(pid)
        
        if not provider:
            provider = Provider(
                pid=pid, 
                impl=bool(int(impl)), 
                priv_key_pem=vsp_priv_keys[pid]
            )
            providers[pid] = provider
            
        if i == 0:
            signal, start_token = provider.originate()
        elif i == len(route) - 1:
            final_token = provider.terminate(signal)
        else:
            signal = provider.receive(signal)
    
    # assert start_token is not None
    # assert final_token is not None
    # assert start_token == final_token
    
    return entry.get('_id')

def get_route_from_bitstring(path: str):
    if not path.isdigit() or set(path) > {'0', '1'}:
        raise Exception('Invalid format string for call path: Accepted values are binary digits')
    return [(i, int(d)) for i, d in enumerate(path)]

def gen_provider_credentials(start: int, num_providers: int):
    keydata = {}
    pki = files.read_json(config.CONF_DIR + '/cas.certs.json')
    
    print(f"> Generating Keys for vsp-{start} to vsp-{num_providers-1}...", end='')
    
    for i in range(start, num_providers):
        pid = f'vsp_{i}'
        rand_ca = pki[constants.INTERMEDIATE_CA_KEY][random.randint(0, len(pki[constants.INTERMEDIATE_CA_KEY]) - 1)]
        sk, csr = certs.client_keygen(name=pid)
        
        signed_cert_str = certs.sign_csr(
            csr_str=csr,
            ca_private_key_str=rand_ca[constants.PRIV_KEY],
            ca_cert_str=rand_ca[constants.CERT_KEY],
            days_valid=90
        )
        
        keydata[pid] = sk
        persistence.store_cert(key=pid, cert=signed_cert_str)
    
    print("DONE")
    return keydata

def init_provider_private_keys(num_providers: int):
    global vsp_priv_keys
    
    modified = False
    vsp_priv_keys = files.read_json(keyfile)
    
    if vsp_priv_keys is False:
        modified = True
        vsp_priv_keys = gen_provider_credentials(start=0, num_providers=num_providers)
    elif type(vsp_priv_keys) is dict and len(vsp_priv_keys.keys()) < num_providers:
        modified = True
        vsp_priv_keys.update(gen_provider_credentials(
            start=len(vsp_priv_keys.keys()),
            num_providers=num_providers
        ))
    
    if modified:
        files.override_json(fileloc=keyfile, data=vsp_priv_keys)

def clean():
    persistence.clean_routes()

def datagen(num_providers: int, deploy_rate: float = 14, force_clean: bool = False):
    if deploy_rate < 0 or deploy_rate > 100:
        raise Exception("Deployment rate can only be a valid number from 0 to 100")
    
    if force_clean is False:
        print("> Checking if routes already exists...", end='')
        if persistence.has_pending_routes():
            print("DONE")
            raise Exception(errors.CALL_ROUTES_ALREADY_GENERTED)
        print("DONE")
    
    clean()
    
    print("> Generate phone network and call routes...", end='')
    routes, stats = network.create(
        num_providers=num_providers, 
        deploy_rate=deploy_rate
    )
    print("DONE")
    
    print("> Saving routes to database...", end='')
    persistence.save_routes(routes)
    print("DONE")
    
    init_provider_private_keys(num_providers=num_providers)
    
def run():
    load_private_keys()
    
    with Pool(processes=processes) as pool:
        start_idx, batch_size = 1, 10
        routes = persistence.retrieve_pending_routes(limit=batch_size)
        
        if len(routes) == 0:
            raise Exception("No route to simulate. Please generate routes")
        
        while len(routes) > 0:
            print(f"> Simulating {len(routes)} routes in Batch {start_idx}")
            simulated_ids = pool.map(simulate_call, routes)
            persistence.mark_simulated(simulated_ids)
            
            routes = persistence.retrieve_pending_routes(limit=batch_size)
            start_idx += 1
            
