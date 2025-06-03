from os import getenv
from dotenv import load_dotenv

from jodi.constants import MODE_OOBSS

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

DEBUG = env('APP_DEBUG', True, dtype=bool)

COMPOSE_NETWORK_ID = "jodi_net"

STORES_KEY = 'jodi.nodes.ms'
EVALS_KEY = 'jodi.nodes.ev'
CPS_KEY = 'sti.nodes.cps'
CR_KEY = 'sti.nodes.cr'
EVAL_KEYSETS_KEY = 'jodi.evals.keysets'

NO_OF_INTERMEDIATE_CAS = env("NO_OF_INTERMEDIATE_CAS", 11)
NUM_CREDS_PER_ICA = env("NO_CREDS_PER_ICA", 680)
CONF_DIR = env("CONF_DIR", "conf")

DB_HOST = env("DB_HOST", "mongo")
DB_PORT = env("DB_PORT", 27017)
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")
DB_NAME = env("DB_NAME", "jodi")

CACHE_HOST = env("CACHE_HOST", "cache")
CACHE_PORT = env("CACHE_PORT", "6379")
CACHE_PASS = env("CACHE_PASS")
CACHE_DB = env("CACHE_DB", "0")

n_ev = env('n_ev', 3)
n_ms = env('n_ms', 3)
FAKE_PROXY = env('FAKE_PROXY', True, dtype=bool)

NODE_IP = env('NODE_IP')
NODE_PORT = env('NODE_PORT', '10433')
NODE_FQDN = env('NODE_FQDN', f'{NODE_IP}:{NODE_PORT}')

EV_PORT = env('EV_PORT', '10430')
MS_PORT = env('MS_PORT', '10431')
CR_PORT = env('CR_PORT', '10432')
CPS_0_PORT = env('CPS_0_PORT', '10433')
CPS_1_PORT = env('CPS_1_PORT', '10434')

SS_DEPLOY_RATE = env('SS_DEPLOY_RATE', 55.96, dtype=float)

def get_container_prefix(mode: str):
    return "oobss-cps-" if mode == MODE_OOBSS else "jodi-node-"

def is_oobss_mode(mode: str):
    return mode == MODE_OOBSS

HOST_APP_PATH = env('HOST_APP_PATH')

# General Parameters
T_MAX_SECONDS = env('T_MAX_SECONDS', 15, dtype=int)
SEC_PARAM_BYTES = env('SEC_PARAM_BYTES', 32, dtype=int)


# Group Signatures
TGS_MSK = env('TGS_MSK')
TGS_GPK = env('TGS_GPK')
TGS_GML = env('TGS_GML')
TGS_GSK = env('TGS_GSK')

# VOPRF Parameters
VOPRF_SK = env('VOPRF_SK')
VOPRF_VK = env('VOPRF_VK')

# OPRF Parameters
KEYLIST_SIZE = env('KEYLIST_SIZE', 10, dtype=int)
ROTATION_INTERVAL_SECONDS = env('ROTATION_INTERVAL_SECONDS', 10, dtype=int)
LIVENESS_WINDOW_SECONDS = env('LIVENESS_WINDOW_SECONDS', 4, dtype=int)
KEY_ROTATION_LABEL = env('KEY_ROTATION_LABEL', 'keyrotation')
STORES_PER_MULTI_CID = env('STORES_PER_MULTI_CID', 1, dtype=int)

# Network Churn
EV_AVAILABILITY = env('EV_AVAILABILITY', 0.99, dtype=float)
MS_AVAILABILITY = env('MS_AVAILABILITY', 0.99, dtype=float)

UP_TIME_DURATION = env('UP_TIME_DURATION', 1, dtype=float)
EV_DOWN_TIME = (UP_TIME_DURATION * (1 - EV_AVAILABILITY)) / EV_AVAILABILITY
MS_DOWN_TIME = (UP_TIME_DURATION * (1 - MS_AVAILABILITY)) / MS_AVAILABILITY

CHURN_INTERVAL_SECONDS = env('CHURN_INTERVAL_SECONDS', min(EV_DOWN_TIME, MS_DOWN_TIME), dtype=float)

EMPTY_TOKEN = env('EMPTY_TOKEN', '-1')
USE_LOCAL_CERT_REPO = env('USE_LOCAL_CERT_REPO', False, dtype=bool)


# OOB-S/S Parameters
OOBSS_PROXY_SPC = env('OOBSS_PROXY_SPC')
OOBSS_PROXY_CPS_FQDN = env('OOBSS_PROXY_CPS_FQDN')
OOBSS_PROXY_CR_SK = env('OOBSS_PROXY_CR_SK')
OOBSS_PROXY_CR_X5U = env('OOBSS_PROXY_CR_X5U')


# Experiment Parameters
CPS_COUNT = env('CPS_COUNT', 10, dtype=int)
HOSTS_FILE = env('HOSTS_FILE', 'deployments/hosts.yml')

AUDIT_SERVER_URL = env("AUDIT_SERVER_URL", "http://auditls/log")
LOG_BATCH_KEY = "jodi.als." + env("LOG_BATCH_KEY")
QUEUE_NAME = env("QUEUE_NAME")
SCHEDULE_INTERVAL_SECONDS = env("SCHEDULE_INTERVAL_SECONDS", 1, dtype=int)
