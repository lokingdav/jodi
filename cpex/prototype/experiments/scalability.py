import os, time, argparse, threading
from cpex.prototype import compose
from cpex import config, constants
from multiprocessing import Pool
from cpex.models import persistence, cache
from cpex.helpers import files
from cpex.prototype.simulations import networked, local

numIters = 10
cache_client = None

deployRate = 14.00
maxRepTrustParams = 10
EXPERIMENT_NUM = 1
EXPERIMENT_PARAMS = {
    1: {
        'node_groups': [(10, 10)],
        'provider_groups': [10],
    },
    3: {
        'node_groups': [(10, 10)],
        'provider_groups': [40],
    }
}

Simulator = None

def get_provider_groups():
    return EXPERIMENT_PARAMS[EXPERIMENT_NUM]['provider_groups']

def get_node_groups():
    return EXPERIMENT_PARAMS[EXPERIMENT_NUM]['node_groups']

def run_datagen():
    provider_groups = get_provider_groups()
    groups = persistence.filter_route_collection_ids(provider_groups)
    with Pool(processes=os.cpu_count()) as pool:
        pool.starmap(
            Simulator.datagen, 
            [(num_provs, deployRate, True) for num_provs in groups]
        )

def simulate(resutlsloc: str, mode: str, params: dict):
    results = []

    node_groups = get_node_groups()
    provider_groups = get_provider_groups()
    
    for node_grp in node_groups:
        Simulator.create_nodes(
            mode=mode,
            num_evs=node_grp[0],
            num_repos=node_grp[1]
        )
        
        # Handle network churn simulation
        stop_churning = threading.Event()
        network_churning = threading.Thread(target=local.network_churn, args=(stop_churning,))
        network_churning.start()
        
        for num_provs in provider_groups:
            print(f"\nRunning simulation with {num_provs}({num_provs * (num_provs - 1) // 2}) call paths and {node_grp[0]} ms, {node_grp[1]} evs")
            results.append(Simulator.run({
                'Num_Provs':num_provs,
                'Num_EVs': node_grp[0],
                'Num_MSs': node_grp[1],
                'mode': mode,
                **params
            }))
        
        stop_churning.set()
        network_churning.join()
            
    files.append_csv(resutlsloc, results)
    print("Results written to", resutlsloc)

def prepare_results_file():
    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/experiment-{EXPERIMENT_NUM}.csv"
    files.write_csv(resutlsloc, [[
        'mode', 
        'Num_Provs', 
        'Num_EVs', 
        'Num_MSs', 
        'n_ev',
        'n_ms',
        'lat_min', 
        'lat_max', 
        'lat_mean', 
        'lat_std', 
        'success_rate', 
        'calls_per_sec'
    ]])
    return resutlsloc

def reset_routes():
    provider_groups = get_provider_groups()
    for num_provs in provider_groups:
        persistence.reset_marked_routes(num_provs)

def set_simulator(args):
    global Simulator, EXPERIMENT_NUM
    
    if args.experiment == 1:
        EXPERIMENT_NUM = 1
        Simulator = local.LocalSimulator()
    else:
        EXPERIMENT_NUM = 3
        Simulator = networked.NetworkedSimulator()

def main(args):
    global cache_client
    
    set_simulator(args)

    run_datagen()
    resutlsloc = prepare_results_file()
    reset_routes()
    
    cache_client = cache.connect()
    cache.set_client(cache_client)
    networked.set_cache_client(cache_client)

    start = time.perf_counter()
    
    for i in range(1, maxRepTrustParams + 1):
        for j in range(1, maxRepTrustParams + 1):
            for _ in range(numIters):
                params = {'n_ev': i, 'n_ms': j}
                print(f"\nIteration {_+1}/{numIters}, {params}")
                simulate(
                    resutlsloc=resutlsloc,
                    mode=constants.MODE_CPEX,
                    params=params
                )

    print(f"Time taken: {time.perf_counter() - start:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', type=int, choices=[1, 3], help='Experiment to run. Either 1 or 3. Default=1', default='1')
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)
    
