import docker, os, argparse, json
from cpex import config
from cpex.models import cache
from pylibcpex import Utils
from multiprocessing import Pool
from typing import Tuple
from cpex.helpers import dht

cache_client = None

def set_cache_client(client):
    global cache_client
    cache_client = client

def get_client():
    return docker.from_env()

def count_containers(prefix):
    client = get_client()
    containers = client.containers.list()
    matching_containers = [container for container in containers if container.name.startswith(prefix)]
    return len(matching_containers)

def add_node(name: str):
    client = get_client()
    node_id = Utils.hash256(name.encode()).hex()
    
    volumes = { config.HOST_APP_PATH: { 'bind': '/app', 'mode': 'rw' }}
    environment = { 'NODE_ID': node_id, 'NODE_FQDN': name }
    command = 'uvicorn [app] --host 0.0.0.0 --port 80 --reload'
    
    if 'atis-' in name:
        command = command.replace('[app]', 'cpex.prototype.stirshaken.cps_server:app')
    elif '-ev' in name:
        command = command.replace('[app]', 'cpex.servers.evaluator:app')
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

def cache_repositories(mode: str):
    cps, ms, ev = [], [], []
    containers = get_client().containers.list()
    for container in containers:
        if not container.name.startswith(config.get_container_prefix(mode)):
            continue
        
        noderec = {
            'id': Utils.hash256(container.name.encode()).hex(),
            'name': container.name,
            'fqdn': container.name,
            'url': f'http://{container.name}'
        }
        
        if 'atis-' in container.name:
            cps.append(noderec)
        elif '-ev' in container.name:
            ev.append(noderec)
        else:
            ms.append(noderec)
            
    # print('CPS', [c.get('name') for c in cps])
    # print('MS', [m.get('name') for m in ms])
    # print('EVALS', [e.get('name') for e in ev])
    
    if cps: cache.save(client=cache_client, key=config.CPS_KEY, value=json.dumps(cps))
    if ms: cache.save(client=cache_client, key=config.STORES_KEY, value=json.dumps(ms))
    if ev: cache.save(client=cache_client, key=config.EVALS_KEY, value=json.dumps(ev))

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
        
    cache_repositories(mode=mode)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, help='Number of nodes to add', required=True)
    parser.add_argument('--mode', type=str, help='Mode of operation', required=True)
    parser.add_argument('--type', type=str, help='Type of node to add: ms or ev if mode is CPEX', required=False)
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
    else:
        add_nodes(args.count, args.mode, args.type)
        