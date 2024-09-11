from os import getenv
from dotenv import load_dotenv

load_dotenv(override=True)

def env(envname, default=""):
    value = getenv(envname)
    return value or default

DB_HOST = env("DB_HOST", "oob_db")
DB_PORT = env("DB_PORT", 27017)
DB_NAME = env("DB_NAME", "murmys")
DB_USER = env("DB_USER", "root")
DB_PASS = env("DB_PASS", "secret")

CPS_TYPE = env("CPS_TYPE", "oob")
CPS_FQDN = env("CPS_FQDN")

ALG = env("ALG", "ES256")

def is_atis():
    return CPS_TYPE == "atis"