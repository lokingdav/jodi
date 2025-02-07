from os import getenv
from dotenv import load_dotenv

from cpex.constants import MODE_ATIS

load_dotenv(override=True)

def env(envname, default="", dtype=None):
    value = getenv(envname)
    value = value if value else default
    if dtype == bool:
        if type(value) == bool:
            return value
        return value.lower() in ['true', '1', 't', 'y', 'yes']
    if dtype == int:
        return int(value)
    if dtype == float:
        return float(value)
    return value

APP_ENV = env('APP_ENV', 'dev')
APP_ENV_PROD = APP_ENV == 'prod'
DEBUG = env('APP_DEBUG', 'true', dtype=bool)

COMPOSE_NETWORK_ID = "cpex_net"
CPEX_DOCKER_IMAGE = "cpex"

STORES_KEY = 'cpex.nodes.ms'
EVALS_KEY = 'cpex.nodes.ev'
CPS_KEY = 'sti.nodes.cps'
EVAL_KEYSETS_KEY = 'cpex.evals.keysets'

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

n_ev = env('n_ev', 3)
n_ms = env('n_ms', 3)
FAKE_PROXY = env('FAKE_PROXY', True, dtype=bool)

NODE_ID = env('NODE_ID')
NODE_FQDN = env('NODE_FQDN')

EV_PORT = env('EV_PORT', '10430')
MS_PORT = env('MS_PORT', '10431')
CR_PORT = env('CR_PORT', '10432')
CPS_PORT = env('CPS_PORT', '10433')

SS_DEPLOY_RATE = env('SS_DEPLOY_RATE', 55.96, dtype=float)

def get_container_prefix(mode: str):
    return "atis-cps-" if mode == MODE_ATIS else "cpex-node-"

def is_atis_mode(mode: str):
    return mode == MODE_ATIS

HOST_APP_PATH = env('HOST_APP_PATH')

# General Parameters
T_MAX_SECONDS = env('T_MAX_SECONDS', 10, dtype=int)
REC_TTL_SECONDS = env('REC_TTL_SECONDS',15, dtype=int)


# Group Signatures
TGS_MSK = env('TGS_MSK')
TGS_GPK = env('TGS_GPK')
TGS_GML = env('TGS_GML')
TGS_GSK = env('TGS_GSK')

# OPRF Parameters
OPRF_KEYLIST_SIZE = env('OPRF_KEYLIST_SIZE', 10, dtype=int)
OPRF_INTERVAL_SECONDS = env('OPRF_INTERVAL_SECONDS', 10, dtype=int)

# Network Churn
EV_AVAILABILITY = env('EV_AVAILABILITY', 0.99, dtype=float)
MS_AVAILABILITY = env('MS_AVAILABILITY', 0.99, dtype=float)

UP_TIME_DURATION = env('UP_TIME_DURATION', 1, dtype=float)
EV_DOWN_TIME = (UP_TIME_DURATION * (1 - EV_AVAILABILITY)) / EV_AVAILABILITY
MS_DOWN_TIME = (UP_TIME_DURATION * (1 - MS_AVAILABILITY)) / MS_AVAILABILITY

CHURN_INTERVAL_SECONDS = env('CHURN_INTERVAL_SECONDS', min(EV_DOWN_TIME, MS_DOWN_TIME), dtype=float)

EMPTY_TOKEN = env('EMPTY_TOKEN', '-1')

