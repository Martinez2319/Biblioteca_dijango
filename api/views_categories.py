import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone

from .db import categories_collection
from .decorators import admin_required

def serialize_category(cat):
    if not cat:
        return None
    cat['id'] = str(cat['_id'])
    cat['_id'] = str(cat['_id'])
    return cat

@require_http_methods(["GET"])
def list_categories(request):
    try:
        cats = list(categories_collection().find())
        return JsonResponse([serialize_category(c) for c in cats], safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@admin_required
def create_category(request):
    try:
        data = json.loads(request.body)
        cat = {
            'name': data.get('name'),
            'slug': data.get('slug'),
            'description': data.get('description', ''),
            'createdAt': datetime.now(timezone.utc)
        }
        result = categories_collection().insert_one(cat)
        cat['_id'] = result.inserted_id
        return JsonResponse(serialize_category(cat))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
@admin_required
def update_category(request, cat_id):
    try:
        data = json.loads(request.body)
        update_data = {}
        for field in ['name', 'slug', 'description']:
            if field in data:
                update_data[field] = data[field]
        
        categories_collection().update_one({'_id': ObjectId(cat_id)}, {'$set': update_data})
        cat = categories_collection().find_one({'_id': ObjectId(cat_id)})
        return JsonResponse(serialize_category(cat))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@admin_required
def delete_category(request, cat_id):
    try:
        categories_collection().delete_one({'_id': ObjectId(cat_id)})
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
