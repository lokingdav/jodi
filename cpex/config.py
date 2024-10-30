from os import getenv
from dotenv import load_dotenv

load_dotenv(override=True)

def env(envname, default=""):
    value = getenv(envname)
    return value or default

COMPOSE_NETWORK_ID = "cpex_net"
CPEX_DOCKER_IMAGE = "cpex"