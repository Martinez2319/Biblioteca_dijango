import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId

from .db import users_collection
from .decorators import admin_required

def serialize_user(user):
    if not user:
        return None
    return {
        'id': str(user['_id']),
        '_id': str(user['_id']),
        'name': user.get('name'),
        'email': user.get('email'),
        'role': user.get('role', 'user'),
        'createdAt': user.get('createdAt').isoformat() if user.get('createdAt') else None
    }

@require_http_methods(["GET"])
@admin_required
def list_users(request):
    try:
        users = list(users_collection().find({}, {'passwordHash': 0}))
        return JsonResponse([serialize_user(u) for u in users], safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
@admin_required
def update_user(request, user_id):
    try:
        data = json.loads(request.body)
        update_data = {}
        for field in ['name', 'email', 'role']:
            if field in data:
                update_data[field] = data[field]
        
        users_collection().update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
        user = users_collection().find_one({'_id': ObjectId(user_id)}, {'passwordHash': 0})
        return JsonResponse(serialize_user(user))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@admin_required
def delete_user(request, user_id):
    try:
        users_collection().delete_one({'_id': ObjectId(user_id)})
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
