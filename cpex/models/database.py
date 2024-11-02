from cpex.config  import DB_USER, DB_PASS, DB_HOST, DB_PORT
from pymongo import MongoClient

def open_db():
    uri = f"mongodb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
    return MongoClient(uri)
                
def insert(dbname, collection, records):
    results = None

    with open_db() as connection:
        db = connection[dbname]
        collection = db[collection]
        results = collection.insert_many(records)
        
    return results.inserted_ids

def load_fabric_keys():
    keys: dict = None
    with open_db() as connection:
        db = connection[DB_NAME]
        collection = db['fabric_keys']
        keys = collection.find_one()
    return keys

