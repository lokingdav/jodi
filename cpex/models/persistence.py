from cpex.config  import DB_USER, DB_PASS, DB_HOST, DB_PORT
from pymongo import MongoClient
from cpex.constants import STI_GA_DB

def open_db():
    uri = f"mongodb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
    return MongoClient(uri)

def get_cps_dbname(cps_id: str):
    return f'cps_' + str(cps_id)
                
def insert(dbname, collection, records):
    results = None

    with open_db() as connection:
        db = connection[dbname]
        collection = db[collection]
        results = collection.insert_many(records)
        
    return results.inserted_ids

def get_cert(key: str):
    with open_db() as connection:
        db = connection[STI_GA_DB]
        collection = db['certificates']
        cert = collection.find_one({'_id': key})
    return cert

def store_cert(key: str, cert: str):
    with open_db() as connection:
        db = connection[STI_GA_DB]
        collection = db['certificates']
        collection.find_one_and_update(
            {'_id': key},
            {'$set': {'cert': cert}},
            upsert=True
        )