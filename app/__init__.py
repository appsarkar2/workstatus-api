import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(os.getenv("MONGO_URI"))
    return _client

def get_db():
    return get_client()[os.getenv("MONGO_DB_NAME", "workstatus_v1")]

def get_users():
    return get_db()["users"]