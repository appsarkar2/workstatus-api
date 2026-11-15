from pymongo import MongoClient
from app.settings import settings

client = MongoClient(settings.mongo_uri)
db = client[settings.mongo_db_name]
collection = db["nsc_monitoring_cases"]

count = collection.count_documents({})
print(f"Total records in MongoDB: {count}")

if count > 0:
    first_doc = collection.find_one()
    print("\nColumn names found in MongoDB:")
    for key in first_doc.keys():
        print(f" - {key}: {first_doc[key]}")
else:
    print("❌ MongoDB is empty. You must upload a CSV first.")