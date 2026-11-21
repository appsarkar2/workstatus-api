import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("backend/.env")

mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("MONGO_DB_NAME", "workstatus_v1")

client = MongoClient(mongo_uri)
db = client[db_name]
collection = db["electrical_works"]

print("Connected to MongoDB Atlas:", db_name)

query = {
    "$or": [
        {"scheme_head": {"$regex": "^augmentation of conductor size$", "$options": "i"}},
        {"scheme_category": {"$regex": "^augmentation of conductor size$", "$options": "i"}}
    ]
}

found_docs = list(collection.find(query))
print(f"Number of documents found matching 'Augmentation of Conductor Size': {len(found_docs)}")

for doc in found_docs:
    print(f" - Found ID: {doc.get('_id')}, head: {doc.get('scheme_head')}, category: {doc.get('scheme_category')}")

result = collection.update_many(
    query,
    {"$set": {"scheme_head": "Augmentation of conductor size of 11kV Feeders", "scheme_category": "Augmentation of conductor size of 11kV Feeders"}}
)

print(f"Number of documents modified: {result.modified_count}")

# Also check for any remaining variations or empty
all_heads = collection.distinct("scheme_head")
print("Distinct scheme_heads currently in database:", all_heads)
