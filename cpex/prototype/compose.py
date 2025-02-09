import docker, os, argparse, json
from cpex import config
from cpex.models import cache
from pylibcpex import Utils
from multiprocessing import Pool
from typing import Tuple
from cpex.helpers import dht, files
import yaml

def get_client():
    return docker.from_env()

def count_containers(prefix):
    client = get_client()
    containers = client.containers.list()
    matching_containers = [container for container in containers if container.name.startswith(prefix)]
    return len(matching_containers)

def add_node(name: str):
    client = get_client()
    
    volumes = { config.HOST_APP_PATH: { 'bind': '/app', 'mode': 'rw' }}
    environment = { 'NODE_FQDN': name }
    command = 'uvicorn [app] --host 0.0.0.0 --port 80 --reload'
    
    if 'atis-' in name:
        command = command.replace('[app]', 'cpex.prototype.stirshaken.cps_server:app')
        command = command.replace('[port]', config.CPS_PORT)
    elif '-ev' in name:
        command = command.replace('[app]', 'cpex.servers.evaluator:app')
        command = command.replace('[port]', config.EV_PORT)
    else:
        command = command.replace('[app]', 'cpex.servers.message_store:app')
        command = command.replace('[port]', config.MS_PORT)
    
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

def save_hosts(mode: str):
    hosts_file = 'automation/hosts.yml'
    if not files.is_empty(hosts_file):
        print("\nautomation/hosts.yml is not empty. Delete it first and rerun the command\n")
        return

    containers = get_client().containers.list()

    # Dictionary that holds just the container-related hosts
    container_hosts = {}
    for container in containers:
        if container.name.startswith(config.get_container_prefix(mode)):
            container_hosts[container.name] = {
                'ansible_host': container.name,
                'ansible_user': 'ubuntu',
            }

    inventory = {
        'all': {
            'hosts': container_hosts
        }
    }

    # Write to file
    with open(hosts_file, 'w') as file:
        yaml.dump(inventory, file)


def remove_repositories(mode: str):
    client = get_client()
    containers = client.containers.list()
    prefix = config.get_container_prefix(mode)
    for container in containers:
        if container.name.startswith(prefix):
            container.stop()
            container.remove()
            print(f"Removed container {container.name}")
            
    cache.save(config.EVALS_KEY, json.dumps([]))
    cache.save(config.STORES_KEY, json.dumps([]))
    
def add_nodes(count: int, mode: str, ntype: str = None):
    if not config.is_atis_mode(mode) and ntype not in ['ms', 'ev']:
        raise ValueError(f"Node type is required for {mode} and must be one of 'ms' or 'ev'")
    
    prefix = config.get_container_prefix(mode)
    if not config.is_atis_mode(mode):
        prefix += ntype + '-'
        
    start_id = count_containers(prefix)
    
    names = [ prefix+str(i) for i in range(start_id, start_id + count) ]
    with Pool(processes= os.cpu_count()) as pool:
        pool.map(add_node, names)
    
def main(args):
    if config.is_atis_mode(args.mode):
        add_nodes(args.count, args.mode)
    else:
        add_nodes(args.count, args.mode, 'ms')
        add_nodes(args.count, args.mode, 'ev')
        
    save_hosts(mode=args.mode)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, help='Number of nodes to add', required=True)
    parser.add_argument('--mode', type=str, help='Mode of operation', required=True)
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
    else:
        main(args)
        # save_hosts(args.mode)
        