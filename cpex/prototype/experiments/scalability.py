import os, time
from cpex.prototype import compose, simulation
from cpex import config, constants
from multiprocessing import Pool
from cpex.models import persistence
from cpex.helpers import files

provider_groups = [10,20 ] #, 200, 400, 800, 1600, 3200]
repo_groups = [10]#, 20, 40, 80, 160, 320]
deploy_rate = 14

def setup_repos(count: int, mode: str):
    prefix = config.get_container_prefix(mode)
    num = compose.count_containers(prefix)
    if num < count:
        print(f"Adding {count - num} repositories")
        compose.add_repositories(count=count - num, mode=mode)

def run_datagen():
    groups = persistence.filter_route_collection_ids(provider_groups)
    with Pool(processes=os.cpu_count()) as pool:
        pool.starmap(
            simulation.datagen, 
            [(num_provs, deploy_rate, True) for num_provs in groups]
        )

def main(resutlsloc: str, mode: str):
    print(f"Running scalability experiment in {mode} mode")
    results = []
    for repo_count in repo_groups:
        setup_repos(repo_count, mode)
        for num_provs in provider_groups:
            print(f"\nRunning simulation with {num_provs}({num_provs * (num_provs - 1) // 2}) providers and {repo_count} repositories")
            results.append(simulation.run(
                num_provs=num_provs,
                repo_count=repo_count,
                mode=mode
            ))
            
    files.append_csv(resutlsloc, results)
    print("Results written to", resutlsloc)
    # compose.remove_repositories(mode=mode)

def prepare_results_file():
    results_folder = os.path.dirname(os.path.abspath(__file__)) + '/results'
    files.create_dir_if_not_exists(results_folder)
    resutlsloc = f"{results_folder}/scalability.csv"
    files.write_csv(resutlsloc, [['mode', 'num_repos', 'num_provs', 'min', 'max', 'mean', 'std', 'success', 'failed']])
    return resutlsloc

def reset_routes():
    for num_provs in provider_groups:
        persistence.reset_marked_routes(num_provs)

if __name__ == "__main__":
    run_datagen()
    resutlsloc = prepare_results_file()
    reset_routes()
    main(resutlsloc=resutlsloc, mode=constants.MODE_CPEX)
    
