import os, time
from cpex.prototype import compose, simulation
from cpex import config, constants
from multiprocessing import Pool
from cpex.models import persistence, cache
from cpex.helpers import files

cache_client = None

provider_groups = [10]
node_groups = [(10, 10)] # tuple of num ev and num ms
deploy_rate = 14

def setup_nodes(count: int, mode: str, ntype: str):
    prefix = config.get_container_prefix(mode)
    if not config.is_atis_mode(mode):
        prefix += ntype + '-'
    num = compose.count_containers(prefix)
    if num < count:
        print(f"Adding {count - num} nodes. Mode: {mode}, Type: {ntype}")
        compose.add_nodes(count=count - num, mode=mode, ntype=ntype)

def run_datagen():
    groups = persistence.filter_route_collection_ids(provider_groups)
    with Pool(processes=os.cpu_count()) as pool:
        pool.starmap(
            simulation.datagen, 
            [(num_provs, deploy_rate, True) for num_provs in groups]
        )

def main(resutlsloc: str, mode: str):
    global cache_client
    cache_client = cache.connect()
    compose.set_cache_client(cache_client)
    
    print(f"Running scalability experiment in {mode} mode")
    results = []
    
    for node_grp in node_groups:
        setup_nodes(node_grp[0], mode, ntype='ev')
        setup_nodes(node_grp[1], mode, ntype='ms')
        compose.cache_repositories(mode=mode)
        
        for num_provs in provider_groups:
            print(f"\nRunning simulation with {num_provs}({num_provs * (num_provs - 1) // 2}) call paths and {node_grp[0]} ms, {node_grp[1]} evs")
            results.append(simulation.run(
                num_provs=num_provs,
                node_grp=node_grp,
                mode=mode
            ))
            
    files.append_csv(resutlsloc, results)
    print("Results written to", resutlsloc)
    # compose.remove_repositories(mode=mode)

def prepare_results_file():
    resutlsloc = f"{os.path.dirname(os.path.abspath(__file__))}/results/scalability.csv"
    files.write_csv(resutlsloc, [['mode', 'num_provs', 'num_ev', 'num_ms', 'lat_min', 'lat_max', 'lat_mean', 'lat_std', 'success', 'failed']])
    return resutlsloc

def reset_routes():
    for num_provs in provider_groups:
        persistence.reset_marked_routes(num_provs)

if __name__ == "__main__":
    run_datagen()
    resutlsloc = prepare_results_file()
    reset_routes()
    main(resutlsloc=resutlsloc, mode=constants.MODE_CPEX)
    
