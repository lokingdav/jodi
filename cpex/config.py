from os import getenv
from dotenv import load_dotenv

from cpex.constants import CPS_MODE_CPEX, CPS_MODE_ATIS

load_dotenv(override=True)

def env(envname, default="", dtype=None):
    value = getenv(envname)
    value = value if value else default
    if dtype == int:
        return int(value)
    return value

BASE_CPS_PORT = env('BASE_CPS_PORT', 10000)

NO_OF_INTERMEDIATE_CAS = env("NO_OF_INTERMEDIATE_CAS", 11)
CONF_DIR = env("CONF_DIR", "conf")

DB_HOST = env("DB_HOST", "db")
DB_PORT = env("DB_PORT", 27017)
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")
DB_NAME = env("DB_NAME", "cpex")

CACHE_HOST = env("CACHE_HOST")
CACHE_PORT = env("CACHE_PORT")
CACHE_PASS = env("CACHE_PASS")
CACHE_DB = env("CACHE_DB")

# CPS Information. Should be different for each CPS node
CPS_ID = env('CPS_ID')
CPS_PORT = env('CPS_PORT')
CPS_MODE = env("CPS_MODE", CPS_MODE_CPEX)
INITIAL_CPS_NODES = env("INITIAL_CPS_NODES", 1, dtype=int)
CPS_BASE_URL = env("CPS_BASE_URL", "http://cpex-cps")

IS_ATIS_MODE = CPS_MODE == CPS_MODE_ATIS

CERT_REPO_BASE_URL = env('CERT_REPO_URL', 'http://cpex-sti-pki:8888')
