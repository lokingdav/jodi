from os import getenv
from dotenv import load_dotenv

load_dotenv(override=True)

def env(envname, default=""):
    value = getenv(envname)
    return value or default

DB_HOST = env("DB_HOST", "oob_db")
DB_PORT = env("DB_PORT", 27017)
DB_NAME = env("DB_NAME", "oobshaken")
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")

ALG = env("ALG", "ES256")

CPS_START_PORT = env("CPS_START_PORT", 11000)
CPS_OP_MODE = env("CPS_OP_MODE", 0)
CPS_SERVICE_ID = env("CPS_SERVICE_ID")
CPS_NODES_COUNT = env("CPS_NODES_COUNT")

def is_atis():
    print("CPS_OP_MODE: ", CPS_OP_MODE)
    return int(CPS_OP_MODE) == 0

def get_cps_service_id():
    return CPS_SERVICE_ID

def get_cps_nodes_count():
    return CPS_NODES_COUNT