import os
from cpex.prototype import compose, simulation
from cpex import config, constants
from multiprocessing import Pool

provider_groups = [100, 200, 400, 800, 1600, 3200]
repo_groups = [10, 20, 40, 80, 160, 320]
deploy_rate = 14

def setup_repos(count: int, mode: str):
    prefix = config.get_container_prefix(mode)
    num = compose.count_containers(prefix)
    if num < count:
        print(f"Adding {count - num} repositories")
        compose.add_repositories(count - num)

def run_datagen():
    with Pool(processes=os.cpu_count()) as pool:
        pool.starmap(
            simulation.datagen, 
            [(num_provs, deploy_rate, True) for num_provs in provider_groups]
        )

def main(mode: str):
    print(f"Running scalability experiment in {mode} mode")
    for repo_count in repo_groups:
        setup_repos(repo_count, mode)
        for num_provs in provider_groups:
            simulation.run(num_provs=num_provs, mode=mode)

    compose.remove_repositories(mode=mode)

if __name__ == "__main__":
    run_datagen()
    # main(constants.MODE_CPEX)
    # main(constants.MODE_ATIS)
