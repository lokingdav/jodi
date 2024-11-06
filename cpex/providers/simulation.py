from multiprocessing import Pool, Manager
from cpex.providers import network
from cpex.models import persistence
from cpex.helpers import errors

processes = 4

def simulate_call(callpath: list):
    return len(callpath)

def clean():
    persistence.clean_routes()

def datagen(num_providers: int, deploy_rate: float = 14, force_clean: bool = False):
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
        routes = persistence.retrieve_pending_routes(limit=1000)
        while len(routes) > 0:
            results = pool.map(simulate_call, routes)
