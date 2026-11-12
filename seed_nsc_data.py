# backend/seed_nsc_data.py
"""
Script to connect to MongoDB and insert 50 dummy records into nsc_monitoring_cases
so the NSC Dashboard has test data to show.
"""
import os
import random
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def seed_data():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "workstatus_v1")
    
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db["nsc_monitoring_cases"]

    class_types = ["A", "B", "C", "D"]
    pole_types = ["Pole", "Non-Pole"]
    delay_days_options = [10, 45, 100]
    statuses = ["in_progress", "completed", "on_hold"]

    dummy_records = []
    for i in range(1, 51):
        record = {
            "application_no": f"NSC-2026-{1000 + i}",
            "region": "Darjeeling Region",
            "division": "Siliguri",
            "ccc": "Hakimpara",
            "class_type": random.choice(class_types),
            "pole_type": random.choice(pole_types),
            "delay_days": random.choice(delay_days_options),
            "quotation_delay": random.choice([2, 5, 12, 20]),
            "wo_delay": random.choice([3, 8, 15, 25]),
            "conn_delay": random.choice([5, 10, 20, 35]),
            "status": random.choice(statuses),
            "phase": random.choice(["1-Phase", "3-Phase"])
        }
        dummy_records.append(record)

    result = collection.insert_many(dummy_records)
    print(f"Successfully inserted {len(result.inserted_ids)} dummy records into nsc_monitoring_cases.")

if __name__ == "__main__":
    seed_data()

