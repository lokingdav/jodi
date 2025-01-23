import random, asyncio, os, time, math
import numpy as np
from cpex.prototype import compose
from multiprocessing import Pool
from typing import Tuple
from cpex.crypto import groupsig
from cpex.prototype import network
from cpex.models import cache, persistence
from cpex.helpers import errors, files, dht
from cpex.prototype.stirshaken import certs
from cpex import config, constants
from cpex.prototype.provider import Provider

gsk, gpk = None, None

def init_worker():
    global gsk, gpk
    dht.set_cache_client(cache.connect())
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()

class NetworkedSimulator:
    def simulate_call_sync(self, options: dict):
        res = asyncio.run(self.simulate_call(options))
        return res
    
    def create_provider_instance(self, pid, impl, mode, options):
        return Provider({
            'pid': pid,
            'impl': bool(int(impl)),
            'mode': mode,
            'log': options.get('log', True),
            'gsk': gsk,
            'gpk': gpk,
            'n_ev': options.get('n_ev'),
            'n_ms': options.get('n_ms')
        })

    async def simulate_call(self, options: dict):
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
                provider = self.create_provider_instance(pid, impl, mode, options)
                
                providers[pid] = provider
                
            if i == 0: # Originating provider
                signal, start_token = await provider.originate()
            elif i == len(route) - 1: # Terminating provider
                final_token = await provider.terminate(signal)
            else: # Intermediate provider
                signal = await provider.receive(signal)
        
        is_correct = start_token == final_token
        latency = 0
        
        if not is_correct:
            print(f"\nProcID: {os.getpid()}, Call path is incorrect. src={signal.From}, dst={signal.To}")
            print(f"Data: {options}\n")

        for provider in providers.values():
            latency += provider.get_latency_ms()
            
        # print(f"Simulated call path of length {len(route)} and latency {latency} ms")
        return (latency, len(route), is_correct)

    def get_route_from_bitstring(self, path: str):
        if not path.isdigit() or set(path) > {'0', '1'}:
            raise Exception('Invalid format string for call path: Accepted values are binary digits')
        return [(i, int(d)) for i, d in enumerate(path)]

    def cleanup(self, collection_id: str = ''):
        persistence.clean_routes(collection_id=collection_id)

    def datagen(self, num_providers: int, deploy_rate: float = 14, force_clean: bool = False):
        print(f'> Generating phone network with {num_providers} providers')

        if deploy_rate < 0 or deploy_rate > 100:
            raise Exception("Deployment rate can only be a valid number from 0 to 100")
        
        if force_clean is False:
            if persistence.has_pending_routes(collection_id=num_providers):
                raise Exception(errors.CALL_ROUTES_ALREADY_GENERTED)
        
        self.cleanup(collection_id=num_providers)
        
        routes, stats = network.create(
            num_providers=num_providers, 
            deploy_rate=deploy_rate
        )
        
        persistence.save_routes(collection_id=num_providers, routes=routes)
        print(f"> Generated phone network and with {num_providers} providers")
     
    def get_pages(self, num_provs: str, limit: int = 1000):
        data = persistence.get_route(collection_id=num_provs, route_id=0)
        if not data:
            raise Exception("Routes needs to be generated first")
        limit = min(limit, data['total'])
        return [(i, i + limit) for i in range(1, data['total']+1, limit)], data['total']   
        
    def run(self, params: dict):
        limit = 1000
        statistics = RunningStats()
        total_calls, total_time = 0, 0
        
        num_provs = params.get('Num_Provs')
        mode = params.get('mode')
        
        with Pool(processes=os.cpu_count()*2, initializer=init_worker) as pool:
            pages, total_items = self.get_pages(num_provs=num_provs, limit=limit)
            
                
            for (start_id, end_id) in pages:
                routes = persistence.retrieve_routes(
                    collection_id=num_provs,
                    start_id=start_id,
                    end_id=end_id,
                    params={**params, 'mode': mode, 'log': False}
                )
            
                if len(routes) == 0:
                    raise Exception("No route to simulate. Please generate routes")
                
                print(f"-> Simulating Call From: {start_id}, To:{end_id}, Length: {len(routes)} calls, Total: {total_items}")

                start_time = time.perf_counter()
                results = pool.map(self.simulate_call_sync, routes)
                total_time += time.perf_counter() - start_time
                total_calls += len(results)
                
                for (latency_ms, len_routes, is_correct) in results:
                    if latency_ms < 1: # filter out routes that do not involve oob
                        continue
                    statistics.update_x(latency_ms)
                    if is_correct:
                        statistics.update_correct()
                
            dp = 2
            
            return [
                mode, 
                num_provs, 
                params.get('Num_EVs'), # EV
                params.get('Num_MSs'), # MS 
                params.get('n_ev'),
                params.get('n_ms'),
                round(statistics.min, dp),
                round(statistics.max, dp),
                round(statistics.mean, dp),
                round(statistics.population_stddev, dp),
                statistics.success_rate, 
                math.ceil(total_calls / total_time) if total_time > 0 else 0
            ]

    def create_nodes(self, mode: str, num_evs: int, num_repos: int):
        prefix = config.get_container_prefix(mode)

        if config.is_atis_mode(mode):
            num = compose.count_containers(prefix)
            if num < num_evs:
                print(f"Adding {num_evs - num} nodes. Mode: {mode}")
                compose.add_nodes(count=num_repos - num, mode=mode)
            return
        
        if num_evs:
            num = compose.count_containers(prefix + 'ev')
            print(f"Adding {num_evs - num} nodes. Mode: {mode}, Type: ev")
            compose.add_nodes(count=num_evs - num, mode=mode, ntype='ev')

        if num_repos:
            num = compose.count_containers(prefix + 'ms')
            print(f"Adding {num_repos - num} nodes. Mode: {mode}, Type: ms")
            compose.add_nodes(count=num_repos - num, mode=mode, ntype='ms')
            
class RunningStats:
    def __init__(self):
        self.count = 0
        self._mean = 0.0
        self._M2 = 0.0
        self._min = float('inf')
        self._max = float('-inf')
        self.correct = 0
        
    def update_correct(self):
        self.correct += 1
            
    def update_x(self, x):
        self.count += 1

        # Update min and max
        if x < self._min:
            self._min = x
        if x > self._max:
            self._max = x

        # Update mean and M2 using Welford's algorithm
        delta = x - self._mean
        self._mean += delta / self.count
        delta2 = x - self._mean
        self._M2 += delta * delta2
        
    @property
    def success_rate(self):
        if self.count == 0:
            return 0
        return (self.correct / self.count) * 100

    @property
    def mean(self):
        return self._mean

    @property
    def min(self):
        return self._min if self.count > 0 else None

    @property
    def max(self):
        return self._max if self.count > 0 else None

    @property
    def sample_variance(self):
        if self.count < 2:
            return 0.0
        return self._M2 / (self.count - 1)

    @property
    def sample_stddev(self):
        return self.sample_variance ** 0.5

    @property
    def population_variance(self):
        if self.count == 0:
            return 0.0
        return self._M2 / self.count

    @property
    def population_stddev(self):
        return self.population_variance ** 0.5
