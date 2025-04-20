from jodi.config  import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from jodi.constants import STATUS_PENDING, STATUS_DONE, CERT_KEY
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

def find_one(collection: str, filter: dict = {}):
    if not collection:
        raise Exception("Collection name is required")
    with open_db() as conn:
        item = conn[DB_NAME][collection].find_one(filter)
    return item
    

def store_cert(key: str, cert: str):
    with open_db() as conn:
        conn[DB_NAME].certs.find_one_and_update(
            {'_id': key},
            {'$set': {'cert': cert}},
            upsert=True
        )

def insert_certs(items: list):
    if len(items) == 0:
        return
    insert(collection="certs", records=items)

def has_pending_routes(collection_id: int):
    collection = f'routes_{collection_id}'
    with open_db() as conn:
        route = conn[DB_NAME][collection].find_one({'status': STATUS_PENDING})
    return route

def clean_routes(collection_id: int = ''):
    # clean up all collections with the prefix 'routes_'
    prefix = f'routes_{collection_id}'
    with open_db() as conn:
        for collection in conn[DB_NAME].list_collection_names():
            if collection.startswith(prefix):
                # Drop the collection
                conn[DB_NAME][collection].drop()

def filter_route_collection_ids(groups: list):
    ids = []
    with open_db() as conn:
        collections = conn[DB_NAME].list_collection_names()
        for group in groups:
            collection = f'routes_{group}'
            if str(collection) not in collections:
                ids.append(group)
    return ids

def get_route(collection_id, route_id):
    collection = f'routes_{collection_id}'
    with open_db() as conn:
        route = conn[DB_NAME][collection].find_one({'_id': route_id})
    return route

def retrieve_routes(collection_id: int, start_id: int, end_id: int, params: dict):
    collection = f'routes_{collection_id}'
    with open_db() as conn:
        routes = list(conn[DB_NAME][collection].find({'_id': {'$gte': start_id, '$lte': end_id}}))
    return [{**r, **params} for r in routes]


def save_routes(collection_id: int, routes: list):
    insert(collection=f'routes_{collection_id}', records=routes)
        
def mark_simulated(collection_id: int, ids: list):
    collection = f'routes_{collection_id}' 
    with open_db() as conn:
        filter = {'_id': {'$in': ids}}
        update = {'$set': {'status': STATUS_DONE}}
        conn[DB_NAME][collection].update_many(filter=filter, update=update)

def reset_marked_routes(collection_id: int):
    collection = f'routes_{collection_id}' 
    with open_db() as conn:
        update = {'$set': {'status': STATUS_PENDING}}
        conn[DB_NAME][collection].update_many({}, update)
        
        
def store_credential(name: str, cred: dict):
    with open_db() as conn:
        conn[DB_NAME].credentials.find_one_and_update(
            {'_id': name},
            {'$set': cred},
            upsert=True
        )

def get_credential(name: str):
    with open_db() as conn:
        cred = conn[DB_NAME].credentials.find_one({'_id': name})
    return cred


def get_cert(key: str):
    cred: dict = get_credential(key)
    return cred.get('cert') if cred else None


def save_metrics(metrics: list):
    insert(collection='scalability_metrics', records=metrics)