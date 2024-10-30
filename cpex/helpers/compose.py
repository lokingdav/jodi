import docker
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

def add_cps_node(id: str):
    name: str = f"cpex_dyn_cps_{id}"
    client = get_client()
    
    if not find_image(name=config.CPEX_DOCKER_IMAGE):
        raise Exception(errors.CPEX_IMAGE_NOT_FOUND)
    
    if find_container(name=name, client=client):
        raise Exception(errors.CPS_ALREADY_EXISTS)
    
    if not find_network(name=config.COMPOSE_NETWORK_ID):
        raise Exception(errors.CPS_NETWORK_NOT_FOUND)
    
    container = client.containers.run(
        name=name,
        detach=True,
        image=config.CPEX_DOCKER_IMAGE,
        network=config.COMPOSE_NETWORK_ID,
        command='uvicorn cpex/servers/cps:app --host 0.0.0.0 --port 80 --reload',
    )
    
    