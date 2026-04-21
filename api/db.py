from pymongo import MongoClient
from django.conf import settings

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.MONGO_URL)
        _db = _client[settings.DB_NAME]
    return _db

def get_collection(name):
    return get_db()[name]

# Collections
def users_collection():
    return get_collection('users')

def books_collection():
    return get_collection('books')

def categories_collection():
    return get_collection('categories')

def access_logs_collection():
    return get_collection('accesslogs')

def donations_collection():
    return get_collection('donations')

def purchases_collection():
    return get_collection('purchases')

def notes_collection():
    return get_collection('notes')

def subscriptions_collection():
    return get_collection('subscriptions')

def remote_sources_collection():
    return get_collection('remotesources')

