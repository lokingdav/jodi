from cpex.prototype import compose, simulation
from cpex import config

repo_groups = [10, 20, 40, 80, 160, 320, 640]
provider_groups = [100, 200, 400, 800, 1600, 3200, 6400]
deploy_rate = 14

def setup_repos(count: int, mode: str):
    prefix = config.get_container_prefix(mode)
    num = compose.count_containers(prefix)
    if num < count:
        print(f"Adding {count - num} repositories")
        compose.add_repositories(count - num)

def run_experiment(num_provs: int, mode: str):
    simulation.datagen(num_providers=num_provs, deploy_rate=deploy_rate, force_clean=True)
    simulation.run(mode=mode)

def main(mode: str):
    for repo_count in repo_groups:
        setup_repos(repo_count, mode)
        for num_provs in provider_groups:
            run_experiment(num_provs, mode)
            
if __name__ == "__main__":
    main('cpex')