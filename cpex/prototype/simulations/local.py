import random, asyncio, os, time, math
import numpy as np
from multiprocessing import Pool
from typing import Tuple
from cpex.crypto import groupsig
from cpex.prototype import network
from cpex.models import cache, persistence
from cpex.helpers import errors, files, dht
from cpex.prototype.stirshaken import certs
from cpex import config, constants
from cpex.prototype.simulations.entities import Provider

gsk, gpk = None, None

def init_worker():
    global gsk, gpk
    dht.set_cache_client(cache.connect())
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()

def simulate_call_sync(options: dict):
    res = asyncio.run(simulate_call(options))
    return res

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
    
    providers, signal, start_token, final_token = {}, None, None, None
    
    for i, (idx, impl) in enumerate(route):
        pid = 'P' + str(idx)
        provider: Provider = providers.get(pid)
        
        if not provider:
            provider = Provider(
                pid=pid, 
                impl=bool(int(impl)),
                mode=mode,
                log=options.get('log', True),
                cache_client=dht.cache_client,
                gsk=gsk,
                gpk=gpk
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
        
    print(f"Simulated call path of length {len(route)} and latency {total} ms")
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
    
def run(num_provs: int, node_grp: Tuple[int, int], mode: str):
    with Pool(processes=5, initializer=init_worker) as pool:
        batch_size = 100
        batch_num = 1

        routes = persistence.retrieve_pending_routes(
            collection_id=num_provs,
            limit=100000,
            mode=mode
        )
        
        print(f"-> Retrieved {len(routes)} routes")
        
        if len(routes) == 0:
            raise Exception("No route to simulate. Please generate routes")
                
        metrics, success, failed = np.array([]), 0, 0
        
        total_calls = 0
        total_time = 0

        # while len(routes) > 0:
        print(f"-> Simulating {len(routes)} routes in batch {batch_num}")
        start_time = time.perf_counter()
        results = pool.map(simulate_call_sync, routes)
        total_time += time.perf_counter() - start_time
        total_calls += len(results)
        
        ids = []
        for (rid, latency_ms, len_routes, is_correct) in results:
            ids.append(rid)
            if latency_ms > 0:
                metrics = np.append(metrics, latency_ms)
                if is_correct:
                    success += 1
                else:
                    failed += 1
        
        print('-> Marking simulated routes')
        # persistence.mark_simulated(
        #     collection_id=num_provs,
        #     ids=ids
        # )
        # batch_num += 1

        print('-> Retrieving pending routes')
        routes = persistence.retrieve_pending_routes(
                collection_id=num_provs,
                mode=mode,
                limit=batch_size
            )
        print('-> Simulation completed')
        dp = 2
        return [
            mode, 
            num_provs, 
            node_grp[0], # EV
            node_grp[1], # MS 
            round(metrics.min(), dp), 
            round(metrics.max(), dp), 
            round(metrics.mean(), dp), 
            round(metrics.std(), dp), 
            success, 
            failed,
            math.ceil(total_calls / total_time) if total_time > 0 else 0
        ]
            
