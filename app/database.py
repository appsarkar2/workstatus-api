# backend/app/database.py
from pymongo import MongoClient
from app.settings import settings

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri)
    return _client


def get_db():
    return get_client()[settings.mongo_db_name]


def get_users():
    return get_db()["users"]