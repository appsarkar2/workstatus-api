# backend/seed_dro_users.py
"""
Script to seed DRO (Darjeeling Region) users with specific permissions and distinct passwords.
"""
from pymongo import MongoClient
from passlib.context import CryptContext
from app.settings import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
client = MongoClient(settings.mongo_uri)
db = client[settings.mongo_db_name]
users_collection = db["users"]

# Define the 5 users with distinct passwords and permissions
dro_users = [
    {
        "username": "DRO_H&R",
        "name": "HR Head Darjeeling",
        "role": "hr_user",
        "region": "Darjeeling Region",
        "allowed_stages": [1],
        "password": "HR@Darj2026!",
        "active": True
    },
    {
        "username": "DRO_FINANCE",
        "name": "Finance Head Darjeeling",
        "role": "finance_user",
        "region": "Darjeeling Region",
        "allowed_stages": [4],
        "password": "Fin@Darj2026!",
        "active": True
    },
    {
        "username": "commerce_manager_1",
        "name": "Commerce Manager 1",
        "role": "commerce_manager",
        "region": "Darjeeling Region",
        "allowed_stages": [2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        "password": "Com1@Darj2026!",
        "active": True
    },
    {
        "username": "commerce_manager_2",
        "name": "Commerce Manager 2",
        "role": "commerce_manager",
        "region": "Darjeeling Region",
        "allowed_stages": [2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        "password": "Com2@Darj2026!",
        "active": True
    },
    {
        "username": "commerce_manager_3",
        "name": "Commerce Manager 3",
        "role": "commerce_manager",
        "region": "Darjeeling Region",
        "allowed_stages": [2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        "password": "Com3@Darj2026!",
        "active": True
    }
]

def seed_users():
    for u in dro_users:
        password = u.pop("password")
        u["password_hash"] = pwd_ctx.hash(password)
        
        # Upsert: Update if exists, Insert if not
        users_collection.update_one(
            {"username": u["username"]},
            {"$set": u},
            upsert=True
        )
        print(f"[OK] Seeded user: {u['username']} | Role: {u['role']} | Pass: {password}")
    
    print("\n[DONE] All 5 DRO users have been created successfully.")

if __name__ == "__main__":
    seed_users()