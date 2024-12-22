import random, asyncio
from multiprocessing import Pool, Manager
from cpex.prototype import network
from cpex.models import persistence
from cpex.helpers import errors, files
from cpex.prototype.stirshaken import certs
from cpex import config, constants
from cpex.prototype.provider import Provider

processes = 4

def simulate_call_sync(entry: dict):
    return asyncio.run(simulate_call(entry=entry))

async def simulate_call(entry: dict):
    route = entry.get('route', [])
    print('CALL ROUTE:', route)
    
    if len(route) == 0:
        raise Exception('Invalid simulation parameter')
    
    if not isinstance(route, list):
        raise Exception("Route parameter must be an instance of a list")
    
    if len(set([p for (p, _) in route])) == 1:
        return entry.get('_id')
    
    message_stores = persistence.get_repositories()
    

    providers, signal, start_token, final_token = {}, None, None, None
    
    for i, (idx, impl) in enumerate(route):
        pid = 'P' + str(idx)
        provider: Provider = providers.get(pid)
        
        if not provider:
            if config.IS_ATIS_MODE:
                cps_url = message_stores[random.randint(0, len(message_stores) - 1)].get('url')
                stores = []
            else:
                stores = message_stores[:]
                cps_url = None

            provider = Provider(
                pid=pid, 
                impl=bool(int(impl)),
                cps_url=cps_url,
                message_stores=stores
            )
            
            providers[pid] = provider
            
        if i == 0:
            signal, start_token = await provider.originate()
        elif i == len(route) - 1:
            final_token = await provider.terminate(signal)
        else:
            signal = await provider.receive(signal)
    
    # assert start_token is not None
    # assert final_token is not None
    # assert start_token == final_token
    
    return entry.get('_id')

def get_route_from_bitstring(path: str):
    if not path.isdigit() or set(path) > {'0', '1'}:
        raise Exception('Invalid format string for call path: Accepted values are binary digits')
    return [(i, int(d)) for i, d in enumerate(path)]

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
    
def run():
    with Pool(processes=processes) as pool:
        start_idx, batch_size = 1, 10
        routes = persistence.retrieve_pending_routes(limit=batch_size)
        
        if len(routes) == 0:
            raise Exception("No route to simulate. Please generate routes")
        
        while len(routes) > 0:
            print(f"> Simulating {len(routes)} routes in Batch {start_idx}")
            simulated_ids = pool.map(simulate_call_sync, routes)
            persistence.mark_simulated(simulated_ids)
            
            routes = persistence.retrieve_pending_routes(limit=batch_size)
            start_idx += 1
            
