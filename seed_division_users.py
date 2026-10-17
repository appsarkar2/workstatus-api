# backend/seed_division_users.py
"""
Create 4 division users - one per division.
Run once to add PUJA Load Demand operators.
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

DIVISION_USERS = [
    {
        "username": "user_st",
        "password": "ST@123",
        "name":     "Siliguri Town Operator",
        "role":     "division_user",
        "division": "Siliguri Town",
    },
    {
        "username": "user_su",
        "password": "SU@123",
        "name":     "Siliguri Sub Urban Operator",
        "role":     "division_user",
        "division": "Siliguri Sub Urban",
    },
    {
        "username": "user_kur",
        "password": "KUR@123",
        "name":     "Kurseong Operator",
        "role":     "division_user",
        "division": "Kurseong",
    },
    {
        "username": "user_darj",
        "password": "DARJ@123",
        "name":     "Darjeeling Operator",
        "role":     "division_user",
        "division": "Darjeeling",
    },
]

for u in DIVISION_USERS:
    users.update_one(
        {"username": u["username"]},
        {"$set": {
            "username":      u["username"],
            "password_hash": pwd.hash(u["password"]),
            "role":          u["role"],
            "name":          u["name"],
            "division":      u["division"],
            "active":        True,
        }},
        upsert=True,
    )
    print(f"OK  {u['role']:15s}  {u['username']:10s}  ({u['division']})")

print(f"\n{len(DIVISION_USERS)} division users ready.")
client.close()