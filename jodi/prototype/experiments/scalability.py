import os, time, argparse, threading
from jodi.prototype import compose
from jodi import config, constants
from multiprocessing import Pool
from jodi.models import persistence, cache
from jodi.helpers import files
from jodi.prototype.simulations import networked, local
from collections import defaultdict

numIters = 1
cache_client = None

nprovs = 100
deployRate = 55.96
maxRepTrustParams = 10
EXPERIMENT_NUM = '1'
EXPERIMENT_PART = ''
EXPERIMENT_PARAMS = {
    '1': {
        'node_groups': [(20, 20)],
        'provider_groups': [nprovs],
    },
    '3': {
        'node_groups': [(10, 10)],
        'provider_groups': [nprovs]
    }
}

experimentState = None
stateFile = f"{os.path.dirname(os.path.abspath(__file__))}/state.json"

Simulator = None

def load_checkpoint():
    global experimentState
    if not experimentState:
        experimentState = files.read_json(fileloc=stateFile, default=defaultdict(dict))
    if EXPERIMENT_NUM in experimentState:
        return experimentState[EXPERIMENT_NUM]
    return {}

def save_checkpoint(params):
    global experimentState
    if EXPERIMENT_NUM in experimentState:
        experimentState[EXPERIMENT_NUM].update(params)
    else:
        experimentState[EXPERIMENT_NUM] = params
    
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

def simulate(resultsloc: str, mode: str, params: dict = {}):
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
        # if EXPERIMENT_NUM == '1':
        #     stop_churning = threading.Event()
        #     network_churning = threading.Thread(target=local.network_churn, args=(stop_churning,))
        #     network_churning.start()
        
        for j in range(j_start, len(provider_groups)):
            num_provs = provider_groups[j]
            if config.is_oobss_mode(mode):
                suffix = f"Num_CPSs: {sum(node_groups[i]) }"
            else:
                suffix = f"Num_EVs: {node_groups[i][0]}, Num_MSs: {node_groups[i][1]}"
                
            print(f"\n Started Simulation. Num_Provs: {num_provs}, {suffix}")

            result = Simulator.run({
                'Num_Provs': num_provs,
                'Num_EVs': node_groups[i][0],
                'Num_MSs': node_groups[i][1],
                'mode': mode,
                **params
            })
            save_result(
                loc=resultsloc, 
                result=result,
                nodes_count=sum(node_groups[i])
            )
            if params.get('summarize'):
                print(result)
                
            print("Results written to", resultsloc)
            save_checkpoint({
                **params,
                'N_ev': node_groups[i][0], 
                'N_ms': node_groups[i][1], 
                'mode': mode,
                'NP_idx': j,
                'NN_idx': i,
            })
        j_start = 0

        # if EXPERIMENT_NUM == '1':
        #     stop_churning.set()
        #     network_churning.join()

        save_checkpoint({'NP_idx': -1}) # Reset NP_idx
    i_start = 0
    save_checkpoint({'NN_idx': -1}) # Reset NN_idx

def save_result(**kwargs):
    resultsloc = kwargs.get('loc')
    result = kwargs.get('result')
    
    if EXPERIMENT_NUM == '3':
        files.append_csv(resultsloc, result)
    else:
        files.append_csv(resultsloc, [result])

def prepare_results_file():
    if EXPERIMENT_NUM not in ['1', '3']:
        raise ValueError('Invalid experiment number')

    filename = f'experiment-{EXPERIMENT_NUM}'
    if EXPERIMENT_NUM == '3':
        filename += f'{EXPERIMENT_PART}'
    filename += '.csv'
    
    resultsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/{filename}"

    statsheader = ['lat_min', 'lat_med', 'lat_max', 'lat_mean', 'lat_std','success_rate','calls_per_sec']
    if EXPERIMENT_NUM == '1':
        headers = ['mode','Num_Provs','Num_EVs','Num_MSs','n_ev','n_ms'] + statsheader
    else:
        headers = ['protocol','latency','hops', 'oob_interaction', 'correct']

    files.write_csv(resultsloc, [headers])

    return resultsloc

def set_simulator(args):
    global Simulator, EXPERIMENT_NUM, EXPERIMENT_PART

    if args.experiment == '1':
        EXPERIMENT_NUM = '1'
        Simulator = local.LocalSimulator()
    else:
        EXPERIMENT_NUM = '3'
        EXPERIMENT_PART = args.experiment[-1]
        Simulator = networked.NetworkedSimulator()

def run_experiment_1(resultsloc):
    prevState = load_checkpoint()
    i_start = prevState.get('n_ev', 2)
    j_start = prevState.get('n_ms', 2)
    iter_start = prevState.get('iter', 0) + 1

    start = time.perf_counter()
    
    for i in range(i_start, maxRepTrustParams + 1):
        for j in range(j_start, maxRepTrustParams + 1):
            for iteration in range(iter_start, numIters + 1):
                params = {'n_ev': i, 'n_ms': j, 'iter': iteration}
                print(f"\n============ Iteration {iteration}/{numIters}, {params} ============")
                start_time = time.perf_counter()
                simulate(resultsloc=resultsloc, mode=constants.MODE_JODI, params=params)
                print(f"\tTime taken: {time.perf_counter() - start_time:.2f} seconds\n=============================================")
            iter_start = 1 # Reset iter_start after first iteration
        j_start = 2 # Reset j_start after first iteration
    i_start = 2 # Reset i_start after first iteration
    delete_state_for_exp()
    print(f"Time taken: {time.perf_counter() - start:.2f} seconds")

def run_experiment_3(resultsloc):
    conf = {
        'resultsloc': resultsloc, 
        'mode': constants.MODE_JODI, 
        'params': {'summarize': False}
    }
    
    if EXPERIMENT_PART == 'a':
        conf['mode'] = constants.MODE_OOBSS
    else:
        conf['params'].update({'n_ev': 3, 'n_ms': 3})
    
    simulate(**conf)
    
    delete_state_for_exp()

def main(args):
    global cache_client
    
    set_simulator(args)

    run_datagen()
    resultsloc = prepare_results_file()
    
    cache_client = cache.connect()
    cache.set_client(cache_client)
    networked.set_cache_client(cache_client)

    if args.experiment == '1':
        run_experiment_1(resultsloc)
    elif args.experiment in ['3a', '3b']:
        run_experiment_3(resultsloc)

def delete_state_for_exp():
    global experimentState
    if not experimentState: return
    experimentState[EXPERIMENT_NUM] = {}
    files.override_json(fileloc=stateFile, data=experimentState)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', type=str, choices=['1', '3a', '3b'], help='Experiment to run. Either 1, 3a or 3b. Default=1', default='1')
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)
    
