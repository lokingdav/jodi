import docker, os, argparse, json
from cpex import config
from cpex.models import cache
from pylibcpex import Utils
from multiprocessing import Pool

def get_client():
    return docker.from_env()

def count_containers(prefix):
    client = get_client()
    containers = client.containers.list()
    matching_containers = [container for container in containers if container.name.startswith(prefix)]
    return len(matching_containers)

def add_repository(repo_id):
    name: str = config.REPO_CONTAINER_PREFIX + str(repo_id)
    client = get_client()
    node_id = Utils.hash160(name.encode()).hex()
    
    volumes = { config.HOST_APP_PATH: {'bind': '/app', 'mode': 'rw'}}
    environment = { 'NODE_ID': node_id, 'REPO_FQDN': name }
    command = 'uvicorn [app] --host 0.0.0.0 --port 80 --reload'
    if config.IS_ATIS_MODE:
        command = command.replace('[app]', 'cpex.prototype.stirshaken.cps_server:app')
    else:
        command = command.replace('[app]', 'cpex.servers.message_store:app')
    
    client.containers.run(
        name=name,
        detach=True,
        image=config.CPEX_DOCKER_IMAGE,
        network=config.COMPOSE_NETWORK_ID,
        environment=environment,
        volumes=volumes,
        command=command
    )
    
    print(f"Started container {name}")

def cache_repositories():
    repos = []
    containers = get_client().containers.list()
    for container in containers:
        if container.name.startswith(config.REPO_CONTAINER_PREFIX):
            repos.append({
                'id': Utils.hash160(container.name.encode()).hex(),
                'name': container.name,
                'fqdn': container.name,
                'url': f'http://{container.name}'
            })
    cache.save('repositories', json.dumps(repos))
    
    
def add_repositories(count: int):
    start_id = count_containers(config.REPO_CONTAINER_PREFIX)
    ids = list(range(start_id, start_id + count))
    with Pool(processes= os.cpu_count()) as pool:
        pool.map(add_repository, ids)
    cache_repositories()
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, help='Number of repositories to add')
    args = parser.parse_args()
    if args.count:
        add_repositories(args.count)
    else:
        print("No arguments provided. Use --count to specify number of repositories to add")