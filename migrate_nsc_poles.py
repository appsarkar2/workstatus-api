# backend/migrate_nsc_poles.py
"""
Migration script to convert existing documents in nsc_monitoring_cases collection
so that `no_of_poles` is properly converted to integer numbers, handling strings,
'(null)', nulls, and missing values.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def parse_no_of_poles(val) -> int:
    if val is None:
        return 0
    s = str(val).strip().lower()
    if s in ('', '(null)', 'null', 'nan', 'none', '0', '-'):
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0

def migrate_poles():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "workstatus_v1")
    
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db["nsc_monitoring_cases"]

    docs = list(collection.find({}))
    print(f"Found {len(docs)} documents in {collection.name}. Starting migration of `no_of_poles`...")

    updated_count = 0
    for doc in docs:
        doc_id = doc["_id"]
        # Check various possible keys
        val = None
        for k in list(doc.keys()):
            if k.lower() == 'no_of_poles' or 'pole' in k.lower():
                val = doc.get(k)
                if val is not None:
                    break

        new_val = max(parse_no_of_poles(val), 0)
        
        # Always set 'no_of_poles' as integer
        collection.update_one(
            {"_id": doc_id},
            {"$set": {"no_of_poles": new_val}}
        )
        updated_count += 1

    print(f"Successfully migrated {updated_count} documents. `no_of_poles` is now stored as integer.")

if __name__ == "__main__":
    migrate_poles()
