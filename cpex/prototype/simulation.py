import random, asyncio, os
import numpy as np
from multiprocessing import Pool

from cpex.prototype import network
from cpex.models import cache, persistence
from cpex.helpers import errors, files
from cpex.prototype.stirshaken import certs
from cpex import config, constants
from cpex.prototype.provider import Provider

def simulate_call_sync(options: dict):
    return asyncio.run(simulate_call(options))

async def simulate_call(options: dict):
    mode: str = options.get('mode')

    if mode not in constants.MODES:
        raise Exception(f"Invalid simulation mode: {mode}")
    
    route = options.get('route', [])
    
    if len(route) == 0:
        raise Exception('Invalid simulation parameter')
    
    if not isinstance(route, list):
        raise Exception("Route parameter must be an instance of a list")
    
    if len(set([p for (p, _) in route])) == 1:
        return options.get('_id')
    
    message_stores = cache.get_all_repositories(mode=mode)

    providers, signal, start_token, final_token = {}, None, None, None
    
    for i, (idx, impl) in enumerate(route):
        pid = 'P' + str(idx)
        provider: Provider = providers.get(pid)
        
        if not provider:
            if config.is_atis_mode(mode):
                cps_url = message_stores[random.randint(0, len(message_stores) - 1)].get('url')
                stores = []
            else:
                stores = message_stores[:]
                cps_url = None

            provider = Provider(
                pid=pid, 
                impl=bool(int(impl)),
                mode=mode,
                cps_url=cps_url,
                message_stores=stores,
                log=options.get('log', True)
            )
            
            providers[pid] = provider
            
        if i == 0: # Originating provider
            signal, start_token = await provider.originate()
        elif i == len(route) - 1: # Terminating provider
            final_token = await provider.terminate(signal)
        else: # Intermediate provider
            signal = await provider.receive(signal)
    
    is_correct = start_token == final_token
    total = 0
    for provider in providers.values():
        total += provider.get_latency_ms()
    
    return (options.get('_id'), total, len(route), is_correct)

def get_route_from_bitstring(path: str):
    if not path.isdigit() or set(path) > {'0', '1'}:
        raise Exception('Invalid format string for call path: Accepted values are binary digits')
    return [(i, int(d)) for i, d in enumerate(path)]

def cleanup(collection_id: str = ''):
    persistence.clean_routes(collection_id=collection_id)

def datagen(num_providers: int, deploy_rate: float = 14, force_clean: bool = False):
    print(f'> Generating phone network with {num_providers} providers')

    if deploy_rate < 0 or deploy_rate > 100:
        raise Exception("Deployment rate can only be a valid number from 0 to 100")
    
    if force_clean is False:
        if persistence.has_pending_routes(collection_id=num_providers):
            raise Exception(errors.CALL_ROUTES_ALREADY_GENERTED)
    
    cleanup(collection_id=num_providers)
    
    routes, stats = network.create(
        num_providers=num_providers, 
        deploy_rate=deploy_rate
    )
    
    persistence.save_routes(collection_id=num_providers, routes=routes)
    print(f"> Generated phone network and with {num_providers} providers")
    
def run(num_provs: int, repo_count: int, mode: str):
    with Pool(processes=os.cpu_count()) as pool:
        batch_size = 1000

        routes = persistence.retrieve_pending_routes(
            collection_id=num_provs,
            limit=batch_size,
            mode=mode
        )
        
        if len(routes) == 0:
            raise Exception("No route to simulate. Please generate routes")
        
        metrics, success, failed = np.array([]), 0, 0

        while len(routes) > 0:
            results = pool.map(simulate_call_sync, routes)
            ids = []
            for (rid, latency_ms, _, is_correct) in results:
                ids.append(rid)
                if latency_ms > 0:
                    metrics = np.append(metrics, latency_ms)
                    if is_correct:
                        success += 1
                    else:
                        failed += 1
                
            persistence.mark_simulated(ids)

            routes = persistence.retrieve_pending_routes(
                collection_id=num_provs,
                mode=mode,
                limit=batch_size
            )
        
        return [mode, repo_count, num_provs, metrics.min(), metrics.max(), metrics.mean(), metrics.std(), success, failed]
            
