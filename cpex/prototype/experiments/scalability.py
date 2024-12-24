import os
from cpex.prototype import compose, simulation
from cpex import config, constants
from multiprocessing import Pool
from cpex.models import persistence
from cpex.helpers import files

provider_groups = [10] #, 200, 400, 800, 1600, 3200]
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
    print(f"Generating data for {groups}")

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
            print(f"Running simulation with {num_provs} providers and {repo_count} repositories")
            results += simulation.run(
                num_provs=num_provs,
                repo_count=repo_count,
                mode=mode
            )
            # files.append_csv(resutlsloc, results)
    print(results)

    compose.remove_repositories(mode=mode)

def prepare_results_file():
    results_folder = os.path.dirname(os.path.abspath(__file__)) + '/results'
    files.create_dir_if_not_exists(results_folder)
    resutlsloc = f"{results_folder}/scalability.csv"
    files.write_csv(resutlsloc, [['mode', 'num_repos', 'num_provs', 'min', 'max', 'mean', 'std', 'success', 'failed']])
    return resutlsloc

if __name__ == "__main__":
    run_datagen()
    resutlsloc = prepare_results_file()
    main(resutlsloc=resutlsloc, mode=constants.MODE_CPEX)
    # main(constants.MODE_ATIS)
