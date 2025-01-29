import time, os, asyncio, json
from cpex.helpers import misc, http, files, dht
from cpex.crypto import libcpex, groupsig
from pylibcpex import Oprf, Utils
from cpex import config, constants
from cpex.models import cache
from multiprocessing import Pool
from cpex.prototype import provider as providerMod
from cpex.prototype.simulations import entities


numIters = 1
cache_client = None
gpk = groupsig.get_gpk()
gsk = groupsig.get_gsk()
n_evs = [2]#, 3, 4, 5]
n_mss = [2]#, 3, 4, 5]

# Sample src, dst and JWT token
src = '16841333538'
dst = '16847000540'

def init_worker():
    cache.set_client(cache_client)

def bench_sync(options):
    return asyncio.run(bench_async(options))
    
async def bench_async(options):
    print(f"Running with {options['num_ev']} EVs and {options['num_ms']} MSs")
    n_ev, n_ms = options['num_ev'], options['num_ms']
    
    params = {
        'impl': False, # force run publish protocol
        'mode': 'cpex',
        'gpk': gpk, 
        'gsk': gsk,
        'n_ev': n_ev,
        'n_ms': n_ms
    }
    
    originating_provider = entities.Provider({'pid': 'P0', **params})
    terminating_provider = entities.Provider({'pid': 'P5', **params})
    
    signal, initial_token = await originating_provider.originate(src=src, dst=dst)
    final_token = await terminating_provider.terminate(signal)
    assert final_token == initial_token, "Tokens do not match"
    pub_compute = originating_provider.get_publish_compute_times()
    ret_compute = terminating_provider.get_retrieve_compute_times()
    
    results = [
        n_ev, 
        n_ms,
        pub_compute['publish'],
        pub_compute['evaluator'],
        pub_compute['msg_store_pub'],
        ret_compute['retrieve'], 
        ret_compute['msg_store_ret']
    ]
    
    return results
    
def create_nodes(num_ev=30, num_ms=30):
    evals, stores = [], []

    for i in range(num_ms):
        name = f'cpex-node-ms-{i}'
        stores.append({
            'id': Utils.hash256(name.encode('utf-8')).hex(),
            'name': name,
            'fqdn': name,
            'url': f'http://{name}'
        })
    if stores:
        cache.save(key=config.STORES_KEY, value=json.dumps(stores))

    for i in range(num_ev):
        name = f'cpex-node-ev-{i}'
        evals.append({
            'id': Utils.hash256(name.encode('utf-8')).hex(),
            'name': name,
            'fqdn': name,
            'url': f'http://{name}'
        })
    if evals:
        cache.save(key=config.EVALS_KEY, value=json.dumps(evals))
    

def main():
    global cache_client
    cache_client = cache.connect()
    cache.set_client(cache_client)
    
    create_nodes()
    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/microbench.csv"
    files.write_csv(resutlsloc, [['Num Evals', 'Num Stores', 'PUB:P', 'PUB:EV', 'PUB:MS', 'RET:P', 'RET:MS']])
    
    print(f"Running {numIters} iterations of the CPEX protocol microbenchmark...")
    start = time.perf_counter()
    params = []

    with Pool(processes=os.cpu_count()*2, initializer=init_worker) as pool:
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