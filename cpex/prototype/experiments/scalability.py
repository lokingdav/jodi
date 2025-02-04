import os, time, argparse, threading
from cpex.prototype import compose
from cpex import config, constants
from multiprocessing import Pool
from cpex.models import persistence, cache
from cpex.helpers import files
from cpex.prototype.simulations import networked, local
from collections import defaultdict

numIters = 1
cache_client = None

deployRate = 55.96
maxRepTrustParams = 10
EXPERIMENT_NUM = 1
EXPERIMENT_PARAMS = {
    1: {
        'simulator': local.LocalSimulator,
        'node_groups': [(20, 20)],
        'provider_groups': [100],
    },
    3: {
        'simulator': networked.NetworkedSimulator,
        'node_groups': [(10, 10)],
        'provider_groups': [10, 20, 40, 80, 160, 320, 640, 1280],
    }
}

experimentState = None
stateFile = f"{os.path.dirname(os.path.abspath(__file__))}/state.json"

Simulator = None

def load_checkpoint():
    global experimentState
    if not experimentState:
        experimentState = files.read_json(fileloc=stateFile, default=defaultdict(dict))
    return experimentState[str(EXPERIMENT_NUM)]

def save_checkpoint(params):
    experimentState[str(EXPERIMENT_NUM)].update(params)
    files.override_json(fileloc=stateFile, data=experimentState)
    

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
    prevState = load_checkpoint()
    i_start = prevState.get('NN_idx', -1) + 1
    j_start = prevState.get('NP_idx', -1) + 1

    node_groups = get_node_groups()
    provider_groups = get_provider_groups()
    
    for i in range(i_start, len(node_groups)):
        Simulator.create_nodes(
            mode=mode,
            num_evs=node_groups[i][0],
            num_repos=node_groups[i][1]
        )
        
        # Handle network churn simulation
        stop_churning = threading.Event()
        network_churning = threading.Thread(target=local.network_churn, args=(stop_churning,))
        network_churning.start()
        
        for j in range(j_start, len(provider_groups)):
            num_provs = provider_groups[j]
            print(f"\nRunning simulation with {num_provs}({num_provs * (num_provs - 1) // 2}) call paths and {node_groups[i][0]} ms, {node_groups[i][1]} evs")
            result = Simulator.run({
                'Num_Provs':num_provs,
                'Num_EVs': node_groups[i][0],
                'Num_MSs': node_groups[i][1],
                'mode': mode,
                **params
            })
            files.append_csv(resutlsloc, [result])
            print(result)
            print("Results written to", resutlsloc)
            save_checkpoint({
                **params,
                'N_ev': node_groups[i][0], 
                'N_ms': node_groups[i][1], 
                'mode': mode,
                'NP_idx': j,
                'NN_idx': i,
            })
        j_start = 0

        stop_churning.set()
        network_churning.join()

        save_checkpoint({'NP_idx': -1}) # Reset NP_idx
    i_start = 0
    save_checkpoint({'NN_idx': -1}) # Reset NN_idx

def prepare_results_file():
    if EXPERIMENT_NUM not in [1, 3]:
        raise ValueError('Invalid experiment number')
    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/experiment-{EXPERIMENT_NUM}.csv"
    prevState = load_checkpoint()
    if prevState: return resutlsloc
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
    
    if EXPERIMENT_NUM == 3:
        raise NotImplementedError("Experiment 3 is not implemented yet")

    run_datagen()
    resutlsloc = prepare_results_file()
    reset_routes()
    
    cache_client = cache.connect()
    cache.set_client(cache_client)
    networked.set_cache_client(cache_client)

    prevState = load_checkpoint()
    i_start = prevState.get('n_ev', 1)
    j_start = prevState.get('n_ms', 1)
    iter_start = prevState.get('iter', 0) + 1

    start = time.perf_counter()
    
    for i in range(i_start, maxRepTrustParams + 1):
        for j in range(j_start, maxRepTrustParams + 1):
            for iteration in range(iter_start, numIters + 1):
                params = {'n_ev': i, 'n_ms': j, 'iter': iteration}
                print(f"\n============ Iteration {iteration}/{numIters}, {params} ============")
                start_time = time.perf_counter()
                simulate(resutlsloc=resutlsloc, mode=constants.MODE_CPEX, params=params)
                print(f"\tTime taken: {time.perf_counter() - start_time:.2f} seconds\n=============================================")
            iter_start = 1 # Reset iter_start after first iteration
        j_start = 1 # Reset j_start after first iteration
    i_start = 1 # Reset i_start after first iteration

    files.delete_file(stateFile)
    print(f"Time taken: {time.perf_counter() - start:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', type=int, choices=[1, 3], help='Experiment to run. Either 1 or 3. Default=1', default='1')
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)
    
