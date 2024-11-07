from multiprocessing import Pool, Manager
from cpex.providers import network
from cpex.models import persistence
from cpex.helpers import errors

processes = 4

def get_route_from_bitstring(path: str):
    if not path.isdigit() or set(path) > {'0', '1'}:
        raise Exception('Invalid format string for call path: Accepted values are binary digits')
    return [(i, int(d)) for i, d in enumerate(path)]

def simulate_call(entry: dict, entities: dict = None):
    return entry.get('_id')

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
        while len(routes) > 0:
            print(f"> Simulating {len(routes)} routes in Batch {start_idx}")
            simulated_ids = pool.map(simulate_call, routes)
            persistence.mark_simulated(simulated_ids)
            routes = persistence.retrieve_pending_routes(limit=batch_size)
            start_idx += 1
