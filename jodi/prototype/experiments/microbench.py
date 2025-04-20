import time, os, asyncio, json
from jodi.helpers import misc, http, files, dht, mylogging
from jodi.crypto import libjodi, groupsig, billing
from pylibjodi import Oprf, Utils
from jodi import config, constants
from jodi.models import cache
from multiprocessing import Pool
from jodi.prototype import provider as providerMod
from jodi.prototype.simulations import entities, local
from jodi.prototype.stirshaken import stirsetup


numIters = 1000
cache_client = None
gpk = groupsig.get_gpk()
gsk = groupsig.get_gsk()
n_evs = [3]
n_mss = [3]

cred, allcreds = stirsetup.load_certs()

def init_worker():
    cache.set_client(cache_client)
    entities.set_evaluator_keys(cache.find(key=config.EVAL_KEYSETS_KEY, dtype=dict))

def bench_sync(options):
    return asyncio.run(bench_async(options))
    
async def bench_async(options):
    n_ev, n_ms = options['num_ev'], options['num_ms']
    
    params = {
        'impl': False, # force run publish protocol
        'mode': 'jodi',
        'gpk': gpk, 
        'gsk': gsk,
        'n_ev': n_ev,
        'n_ms': n_ms,
        'cr': {'x5u': 'https://example.com/ev1.crt', 'sk': cred['sk']},
        'cps': {'fqdn': 'example.com'},
        'bt': billing.create_endorsed_token(config.VOPRF_SK),
    }

    logger = mylogging.create_stream_logger('microbench')
    
    originating_provider = entities.Provider({'pid': 'P0', 'logger': logger, 'next_prov': (5, 0), **params})
    terminating_provider = entities.Provider({'pid': 'P5', 'logger': logger, **params})
    
    signal, initial_token = await originating_provider.originate() # will originate with random src and dst
    final_token = await terminating_provider.terminate(signal)
    # print(f"Initial token: {initial_token}\n")
    # print(f"Final token: {final_token}\n")
    # mylogging.print_logs(logger)
    assert final_token == initial_token, "Tokens do not match"
    pub_compute = originating_provider.get_publish_compute_times()
    ret_compute = terminating_provider.get_retrieve_compute_times()
    total_time = originating_provider.get_latency_ms() + terminating_provider.get_latency_ms()
    
    results = [
        n_ev, 
        n_ms,
        
        pub_compute['provider'],
        pub_compute['evaluator'],
        pub_compute['message_store'],
        
        ret_compute['provider'], 
        ret_compute['evaluator'],
        ret_compute['message_store'],
        
        total_time
    ]
    
    return results

def main():
    global cache_client
    cache_client = cache.connect()
    cache.set_client(cache_client)
    
    simulator = local.LocalSimulator()
    simulator.create_nodes(
        mode=constants.MODE_JODI, 
        num_evs=20, 
        num_repos=20
    )

    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/experiment-2.csv"
    files.write_csv(resutlsloc, [['n', 'm', 'PUB:P', 'PUB:EV', 'PUB:MS', 'RET:P', 'RET:EV', 'RET:MS', 'Total']])
    
    print(f"Running {numIters} iterations of the jodi protocol microbenchmark...")
    start = time.perf_counter()
    params = []

    with Pool(processes=os.cpu_count(), initializer=init_worker) as pool:
        for _ in range(numIters):
            for n_ev in n_evs:
                for n_ms in n_mss:
                    params.append({'num_ms': n_ms, 'num_ev': n_ev})
        results = pool.map(bench_sync, params)
        files.append_csv(resutlsloc, results)

    end = round(time.perf_counter() - start, 2)
    print(f"Results have been saved to {resutlsloc}.\nTotal time taken: {end} seconds.")

if __name__ == '__main__':
    main()