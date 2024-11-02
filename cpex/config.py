from os import getenv
from dotenv import load_dotenv

load_dotenv(override=True)

def env(envname, default=""):
    value = getenv(envname)
    return value or default

COMPOSE_NETWORK_ID = "cpex_net"
CPEX_DOCKER_IMAGE = "cpex"

NO_OF_INTERMEDIATE_CAS = env("NO_OF_INTERMEDIATE_CAS", 11)
PKI_CONFIG_FILE = env("PKI_CONFIG_FILE", "certs.json")

DB_HOST = env("DB_HOST", "127.0.0.1")
DB_PORT = env("DB_PORT", 27017)
DB_NAME = env("DB_NAME", "cpex")
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")