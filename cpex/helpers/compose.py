import docker, os
from cpex import config
from cpex.helpers import errors

def get_client():
    return docker.from_env()

def find_container(name: str, client: docker.client = None):
    client = get_client() if not client else client
    try:
        return client.containers.get(name)
    except:
        return None
    
def find_network(name: str, client: docker.client = None):
    client = get_client() if not client else client
    try:
        return client.networks.get(name)
    except:
        return None
    
def find_image(name: str, client: docker.client = None):
    client = get_client() if not client else client
    try:
        return client.images.get(name)
    except:
        return None

def add_cps_node(cps_id: int):
    name: str = f"cpex-cps-{cps_id}"
    client = get_client()
    
    if not find_image(name=config.CPEX_DOCKER_IMAGE):
        raise Exception(errors.CPEX_IMAGE_NOT_FOUND)
    
    if find_container(name=name, client=client):
        raise Exception(errors.CPS_ALREADY_EXISTS)
    
    if not find_network(name=config.COMPOSE_NETWORK_ID):
        raise Exception(errors.CPS_NETWORK_NOT_FOUND)
    
    port = int(config.BASE_CPS_PORT) + int(cps_id)
    client.containers.run(
        name=name,
        detach=True,
        image=config.CPEX_DOCKER_IMAGE,
        network=config.COMPOSE_NETWORK_ID,
        ports={'8888/tcp': ('0.0.0.0', port)},
        environment={'CPS_ID': cps_id, 'CPS_PORT': port},
        volumes={os.path.abspath('./'): {'bind': '/app', 'mode': 'rw'}},
        command='uvicorn cpex.servers.cps:app --host 0.0.0.0 --port 8888 --reload'
    )
    
    