"""
Creates/updates the first 10 users with hashed passwords.
Run once:  python seed_users.py
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from passlib.context import CryptContext

load_dotenv()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME", "workstatus_v1")]
users = db["users"]

users.create_index("username", unique=True)

SEED = [
    ("superadmin", "Super@123", "super_admin", "Super Admin"),
    ("admin1",     "Admin@123", "admin",       "Admin One"),
    ("admin2",     "Admin@123", "admin",       "Admin Two"),
    ("manager1",   "Mgr@123",   "manager",     "Manager One"),
    ("manager2",   "Mgr@123",   "manager",     "Manager Two"),
    ("manager3",   "Mgr@123",   "manager",     "Manager Three"),
    ("user1",      "User@123",  "user",        "User One"),
    ("user2",      "User@123",  "user",        "User Two"),
    ("user3",      "User@123",  "user",        "User Three"),
    ("user4",      "User@123",  "user",        "User Four"),
]

for username, password, role, name in SEED:
    users.update_one(
        {"username": username},
        {"$set": {
            "username": username,
            "password_hash": pwd.hash(password),
            "role": role,
            "name": name,
            "active": True,
        }},
        upsert=True,
    )
    print(f"OK  {role:12s}  {username:12s}  /  {password}")

print("\nAll 10 users ready.")
client.close()