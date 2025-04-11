import random, asyncio, os, time, math, json, atexit
import numpy as np
from multiprocessing import Pool
from cpex.crypto import groupsig, billing
from cpex.prototype import network
from cpex.models import cache, persistence
from cpex.helpers import errors, mylogging, http
from cpex.prototype.stirshaken import stirsetup
from cpex import config, constants
from cpex.prototype import provider as providerModule
from cpex.prototype.simulations import entities
from cpex.prototype.scripts import setup

gsk, gpk = None, None
credentials = None
call_placement_services = []
certificate_repos = []
cache_client = None

def set_cache_client(client):
    global cache_client
    cache_client = client

def init_worker():
    global gsk, gpk, call_placement_services, certificate_repos, credentials
    cache.set_client(cache_client)
    gsk, gpk = groupsig.get_gsk(), groupsig.get_gpk()
    call_placement_services = cache.find(key=config.CPS_KEY, dtype=dict) or []
    certificate_repos = cache.find(key=config.CR_KEY, dtype=dict) or []
    _, credentials = stirsetup.load_certs()
    entities.set_evaluator_keys(cache.find(key=config.EVAL_KEYSETS_KEY, dtype=dict))
    
    if not http.keep_alive_session:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        http.set_session(http.create_session(event_loop=loop))
        
def teardown_worker(args):
    print(f"{os.getpid()}: teardown worker")
    loop = asyncio.get_event_loop()
    if loop and http.keep_alive_session:
        loop.run_until_complete(http.keep_alive_session.close())
        loop.close()
    
class NetworkedSimulator:
    def simulate_call_sync(self, options: dict):
        # print('Simulating call with options', options)
        res = self.simulate_call(options)
        return res
    
    def create_prov_params(self, pid, impl, mode, options, next_prov):
        if call_placement_services:
            cps = random.choice(call_placement_services)
        else:
            cps = {'url': 'http://localhost', 'fqdn': 'localhost'}
        
        if certificate_repos:
            cr = random.choice(certificate_repos)
        else:
            cr = {'url': 'http://localhost', 'fqdn': 'localhost'}
            
        i = random.randint(0, config.NO_OF_INTERMEDIATE_CAS * config.NUM_CREDS_PER_ICA - 1)
        ck = f"{constants.OTHER_CREDS_KEY}-{i}" 
        cred = credentials[ck]
        return {
            'pid': pid,
            'impl': bool(int(impl)),
            'mode': mode,
            'gsk': gsk,
            'gpk': gpk,
            'n_ev': options.get('n_ev'),
            'n_ms': options.get('n_ms'),
            'next_prov': next_prov,
            'cps': { 'url': cps['url'], 'fqdn': cps['fqdn'] } if cps else None,
            'cr': {'x5u': cr['url'] + f'/certs/{ck}', 'sk': cred['sk']},
            'bt': billing.create_endorsed_token(config.VOPRF_SK),
        }
        
    def create_provider_instance(self, pid, impl, mode, options, next_prov):
        params = self.create_prov_params(
            pid=pid, 
            impl=impl, 
            mode=mode, 
            options=options, 
            next_prov=next_prov
        )
        return providerModule.Provider(params)

    def simulate_call(self, options: dict):
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
        
        logger = mylogging.create_stream_logger('simulator')
        logger.debug(f"Simulating call with route: {route}")
        
        signal, start_token, final_token, latency, oob = None, None, None, 0, 0
        
        loop = asyncio.get_event_loop()

        for i, (idx, impl) in enumerate(route):
            provider = self.create_provider_instance(
                pid='P' + str(idx), 
                impl=impl, 
                mode=mode, 
                options=options, 
                next_prov=route[i + 1] if i + 1 < len(route) else None
            )
            provider.logger = logger

            if i == 0: # Originating provider
                signal, start_token = loop.run_until_complete(provider.originate())
            elif i == len(route) - 1: # Terminating provider
                final_token = loop.run_until_complete(provider.terminate(signal))
            else: # Intermediate provider
                signal = loop.run_until_complete(provider.receive(signal)) 

            lat = provider.get_latency_ms()
            latency += lat
            oob += 1 if lat > 0 else 0
            provider.reset()
            
        is_correct = int(start_token == final_token)
                
        logger.debug(f"Total latency for call = {latency} ms")

        # if not is_correct:
        # mylogging.print_logs(logger)
            
        mylogging.close_logger(logger)

        return (mode, round(latency, 3), len(route), oob, is_correct)

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
        return [(i, i + limit-1) for i in range(1, data['total']+1, limit)], data['total']   
    
    def validate_node_counts(self, **kwargs):
        mode = kwargs.get('mode')
        num_evs = kwargs.get('num_evs')
        num_mss = kwargs.get('num_mss')
        
        if config.is_atis_mode(mode):
            cps = cache.find(key=config.CPS_KEY, dtype=dict)
            assert cps and len(cps) == num_evs + num_mss
        else:
            evs = cache.find(key=config.EVALS_KEY, dtype=dict)
            assert evs and len(evs) == num_evs
            ms = cache.find(key=config.STORES_KEY, dtype=dict)
            assert ms and len(ms) == num_mss
    
    def run(self, params: dict):
        limit = 1000
        statistics = RunningStats()
        total_calls, total_time = 0, 0
        
        num_provs = params.get('Num_Provs')
        mode = params.get('mode')
        
        unsummarized_results = []
        should_summarize = params.get('summarize', True)
        
        self.validate_node_counts(
            num_evs=params.get('Num_EVs'),
            num_mss=params.get('Num_MSs'),
            mode=mode
        )
        num_processes = os.cpu_count() * 2
        with Pool(processes=num_processes, initializer=init_worker) as pool:
            pages, total_items = self.get_pages(num_provs=num_provs, limit=limit)
            progress = 0
            # print('pages', pages)
            for (start_id, end_id) in pages:
                routes = persistence.retrieve_routes(
                    collection_id=num_provs,
                    start_id=start_id,
                    end_id=end_id,
                    params={**params, 'mode': mode}
                )
            
                if len(routes) == 0:
                    raise Exception("No route to simulate. Please generate routes")
                
                progress += len(routes)
                progress_percent = round((progress / total_items) * 100, 2)
                
                print(f"-> Simulating Call From: {start_id}, To:{end_id}, Length: {len(routes)} calls, Total: {progress}/{total_items} ({progress_percent}%)")

                start_time = time.perf_counter()
                results = pool.map(self.simulate_call_sync, routes)
                total_time += time.perf_counter() - start_time
                total_calls += len(results)
                
                if should_summarize:
                    for (md, latency_ms, len_routes, oob, is_correct) in results:
                        if latency_ms == 0: # filter out routes that do not involve oob
                            continue
                        statistics.update_x(latency_ms)
                        if is_correct:
                            statistics.update_correct()
                else:
                    unsummarized_results.extend(results)
                    
            dp = 3

            print('time taken', total_time)
            print('total calls', total_calls)
            
            if should_summarize:
                return [
                    mode, # 0
                    total_calls, # 1
                    params.get('Num_EVs'), # 2
                    params.get('Num_MSs'), # 3 
                    params.get('n_ev'), # 4
                    params.get('n_ms'), # 5
                    round(statistics.min, dp), # 6
                    round(statistics.median, dp), # 7
                    round(statistics.max, dp), # 8
                    round(statistics.mean, dp),
                    round(statistics.population_stddev, dp),
                    round(statistics.success_rate, dp),
                    math.ceil(total_calls / total_time) if total_time > 0 else 0
                ]
            else:
                return unsummarized_results

    def create_nodes(self, **kwargs):
        nodes = setup.get_node_hosts()
        cache.save(key=config.CPS_KEY, value=json.dumps(nodes.get(config.CPS_KEY)))
        cache.save(key=config.EVALS_KEY, value=json.dumps(nodes.get(config.EVALS_KEY)))
        cache.save(key=config.STORES_KEY, value=json.dumps(nodes.get(config.STORES_KEY)))
        cache.save(key=config.CR_KEY, value=json.dumps(nodes.get(config.CR_KEY)))
        # print("EV", nodes[config.EVALS_KEY])
        # print("MS", nodes[config.STORES_KEY])
        # print("CPS", nodes[config.CPS_KEY])
            
class RunningStats:
    def __init__(self):
        self.correct = 0
        self.values = []
        
    def update_correct(self):
        self.correct += 1
            
    def update_x(self, x):
        self.values.append(x)

    @property
    def median(self):
        return np.median(self.values)

    @property
    def success_rate(self):
        if len(self.values) == 0:
            return 0
        return (self.correct / len(self.values)) * 100

    @property
    def mean(self):
        return np.mean(self.values)

    @property
    def min(self):
        return np.min(self.values)

    @property
    def max(self):
        return np.max(self.values)

    @property
    def sample_variance(self):
        return np.var(self.values)

    @property
    def sample_stddev(self):
        return self.sample_variance ** 0.5

    @property
    def population_variance(self):
        return np.var(self.values)

    @property
    def population_stddev(self):
        return self.population_variance ** 0.5