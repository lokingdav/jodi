from os import getenv
from dotenv import load_dotenv

from cpex.constants import MODE_ATIS

load_dotenv(override=True)

def env(envname, default="", dtype=None):
    value = getenv(envname)
    value = value if value else default
    if dtype == bool:
        return value.lower() in ['true', '1', 't', 'y', 'yes']
    if dtype == int:
        return int(value)
    if dtype == float:
        return float(value)
    return value

DEBUG = env('APP_DEBUG', 'true', dtype=bool)

CPEX_VERSION = env('CPEX_VERSION', '1.0.0')
BASE_REPO_PORT = env('BASE_REPO_PORT', 10000)
COMPOSE_NETWORK_ID = "cpex_net"
CPEX_DOCKER_IMAGE = "cpex"

STORES_KEY = 'cpex.nodes.ms'
EVALS_KEY = 'cpex.nodes.ev'
CPS_KEY = 'atis.cps'

NO_OF_INTERMEDIATE_CAS = env("NO_OF_INTERMEDIATE_CAS", 11)
CONF_DIR = env("CONF_DIR", "conf")

DB_HOST = env("DB_HOST", "mongo")
DB_PORT = env("DB_PORT", 27017)
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")
DB_NAME = env("DB_NAME", "cpex")

CACHE_HOST = env("CACHE_HOST", "cache")
CACHE_PORT = env("CACHE_PORT", "6379")
CACHE_PASS = env("CACHE_PASS")
CACHE_DB = env("CACHE_DB", "0")

# CPS Information. Should be different for each CPS node
NODE_ID = env('NODE_ID')
REPO_PORT = env('REPO_PORT')
REPO_FQDN = env('REPO_FQDN')

REPOSITORIES_COUNT = env("REPOSITORIES_COUNT", 1, dtype=int)
CPS_BASE_URL = env("CPS_BASE_URL", "http://cpex-cps")

def get_container_prefix(mode: str):
    return "atis-cps-" if mode == MODE_ATIS else "cpex-node-"

def is_atis_mode(mode: str):
    return mode == MODE_ATIS

HOST_APP_PATH = env('HOST_APP_PATH')

CERT_REPO_BASE_URL = env('CERT_REPO_URL', 'http://cert-repo')

# General Parameters
T_MAX_SECONDS = env('T_MAX_SECONDS', 10, dtype=int)
REC_TTL_SECONDS = env('REC_TTL_SECONDS',15, dtype=int)
REPLICATION = env('REPLICATION', 3)

# Group Signatures
TGS_MSK = env('TGS_MSK')
TGS_GPK = env('TGS_GPK')
TGS_GML = env('TGS_GML')
TGS_GSK = env('TGS_GSK')

# OPRF Parameters
OPRF_KEYLIST_SIZE = env('OPRF_KEYLIST_SIZE', 10, dtype=int)
OPRF_INTERVAL_SECONDS = env('OPRF_INTERVAL_SECONDS', 10, dtype=int)
OPRF_EV_PARAM = env('OPRF_EV_PARAM', 2)


# Network Churn
EV_AVAILABILITY = env('EV_AVAILABILITY', 0.99, dtype=float)
MS_AVAILABILITY = env('MS_AVAILABILITY', 0.99, dtype=float)

UP_TIME_DURATION = env('UP_TIME_DURATION', 1, dtype=float)
EV_DOWN_TIME = (UP_TIME_DURATION * (1 - EV_AVAILABILITY)) / EV_AVAILABILITY
MS_DOWN_TIME = (UP_TIME_DURATION * (1 - MS_AVAILABILITY)) / MS_AVAILABILITY

CHURN_INTERVAL_SECONDS = env('CHURN_INTERVAL_SECONDS', min(EV_DOWN_TIME, MS_DOWN_TIME), dtype=float)
