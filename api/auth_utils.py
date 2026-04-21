import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from bson import ObjectId
from .db import users_collection

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id):
    payload = {
        'id': str(user_id),
        'exp': datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        return payload.get('id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_by_id(user_id):
    try:
        user = users_collection().find_one({'_id': ObjectId(user_id)})
        if user:
            user['id'] = str(user['_id'])
            del user['_id']
            if 'passwordHash' in user:
                del user['passwordHash']
        return user
    except:
        return None

def serialize_user(user):
    if not user:
        return None
    return {
        'id': str(user.get('_id', user.get('id'))),
        'name': user.get('name'),
        'email': user.get('email'),
        'role': user.get('role', 'user')
    }
