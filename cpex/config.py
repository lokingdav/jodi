from os import getenv
from dotenv import load_dotenv

from cpex.constants import CPS_MODE_CPEX

load_dotenv(override=True)

def env(envname, default=""):
    value = getenv(envname)
    return value or default

COMPOSE_NETWORK_ID = "cpex_net"
CPEX_DOCKER_IMAGE = "cpex"
BASE_CPS_PORT = env('BASE_CPS_PORT', 10000)

NO_OF_INTERMEDIATE_CAS = env("NO_OF_INTERMEDIATE_CAS", 11)
CONF_DIR = env("CONF_DIR", "conf")

DB_HOST = env("DB_HOST", "db")
DB_PORT = env("DB_PORT", 27017)
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")

# CPS Information. Should be different for each CPS node
CPS_ID = env('CPS_ID')
CPS_PORT = env('CPS_PORT')
CPS_MODE = env("CPS_MODE", CPS_MODE_CPEX)


CERT_REPO_BASE_URL = env('CERT_REPO_URL', 'http://cpex-sti-pki:8888')
