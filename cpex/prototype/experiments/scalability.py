import os, time, argparse
from cpex.prototype import compose
from cpex import config, constants
from multiprocessing import Pool
from cpex.models import persistence, cache
from cpex.helpers import files
from cpex.prototype.simulations import networked, local

cache_client = None

provider_groups = [10]
node_groups = [(10, 10)] # tuple of num ev and num ms
deploy_rate = 14
n_param = 10

Simulator = None
simulation_type = 'local'

def run_datagen():
    groups = persistence.filter_route_collection_ids(provider_groups)
    with Pool(processes=os.cpu_count()) as pool:
        pool.starmap(
            Simulator.datagen, 
            [(num_provs, deploy_rate, True) for num_provs in groups]
        )

def simulate(resutlsloc: str, mode: str, params: dict):
    global cache_client
    cache_client = cache.connect()
    compose.set_cache_client(cache_client)
    local.set_cache_client(cache_client)
    
    results = []
    
    for node_grp in node_groups:
        Simulator.create_nodes(
            mode=mode,
            num_evs=node_grp[0],
            num_repos=node_grp[1]
        )
        
        for num_provs in provider_groups:
            print(f"\nRunning simulation with {num_provs}({num_provs * (num_provs - 1) // 2}) call paths and {node_grp[0]} ms, {node_grp[1]} evs")
            results.append(Simulator.run({
                'Num_Provs':num_provs,
                'Num_EVs': node_grp[0],
                'Num_MSs': node_grp[1],
                'mode': mode,
                **params
            }))
            
    files.append_csv(resutlsloc, results)
    print("Results written to", resutlsloc)

def prepare_results_file():
    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/scalability.csv"
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
    for num_provs in provider_groups:
        persistence.reset_marked_routes(num_provs)

def main(sim_type: str):
    global Simulator
    Simulator = networked.NetworkedSimulator() if sim_type == 'net' else local.LocalSimulator()
    
    run_datagen()
    resutlsloc = prepare_results_file()
    reset_routes()

    start = time.perf_counter()
    
    for i in range(1, n_param+1):
        for j in range(1, n_param+1):
            simulate(
                resutlsloc=resutlsloc, 
                mode=constants.MODE_CPEX, 
                params={'n_ev': i, 'n_ms': j}
            )
            
    print(f"Time taken: {time.perf_counter() - start:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', type=str, help='Simulation type. Either net or loc. Default=loc', default='loc')
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args.type)
    
