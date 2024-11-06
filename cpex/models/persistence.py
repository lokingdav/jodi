from cpex.config  import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from cpex.constants import STATUS_PENDING, STATUS_DONE
from pymongo import MongoClient

def open_db():
    uri = f"mongodb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
    return MongoClient(uri)

def get_cps_dbname(cps_id: str):
    return f'cps_' + str(cps_id)
                
def insert(collection, records):
    with open_db() as conn:
        results = conn[DB_NAME][collection].insert_many(records)
    return results.inserted_ids

def get_cert(key: str):
    with open_db() as conn:
        cert = conn[DB_NAME].certs.find_one({'_id': key})
    return cert

def store_cert(key: str, cert: str):
    with open_db() as conn:
        conn[DB_NAME].certs.find_one_and_update(
            {'_id': key},
            {'$set': {'cert': cert}},
            upsert=True
        )
        
def has_pending_routes():
    with open_db() as conn:
        route = conn[DB_NAME].routes.find_one({'status': STATUS_PENDING})
    return route

def retrieve_pending_routes(limit:int = 1000):
    with open_db() as conn:
        routes = list(conn[DB_NAME].routes.find({'status': STATUS_PENDING}, limit=limit))
    return routes

def save_routes(routes: list):
    insert(collection='routes', records=routes)
    
def clean_routes():
    with open_db() as conn:
        conn[DB_NAME].routes.delete_many({})
        
def mark_simulated(ids):
    with open_db() as conn:
        filter = {'_id': {'$in': ids}}
        update = {'$set': {'status': STATUS_DONE}}
        conn[DB_NAME].routes.update_many(filter=filter, update=update)