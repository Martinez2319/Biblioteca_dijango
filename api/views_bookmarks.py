import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone

from .db import get_collection
from .decorators import auth_required

def bookmarks_collection():
    return get_collection('bookmarks')

@require_http_methods(["GET"])
@auth_required
def get_bookmarks(request, book_id):
    """Obtener marcadores de un libro"""
    try:
        user_id = request.user_data.get('id')
        bookmarks = list(bookmarks_collection().find({
            'userId': user_id,
            'bookId': book_id
        }).sort('page', 1))
        
        result = []
        for b in bookmarks:
            result.append({
                'id': str(b['_id']),
                'page': b.get('page', 1),
                'note': b.get('note', ''),
                'createdAt': b.get('createdAt').isoformat() if b.get('createdAt') else None
            })
        
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def create_bookmark(request, book_id):
    """Crear marcador"""
    try:
        user_id = request.user_data.get('id')
        data = json.loads(request.body)
        
        page = int(data.get('page', 1))
        note = data.get('note', '').strip()
        
        # Verificar si ya existe marcador en esta página
        existing = bookmarks_collection().find_one({
            'userId': user_id,
            'bookId': book_id,
            'page': page
        })
        
        if existing:
            return JsonResponse({'error': 'Ya existe un marcador en esta página'}, status=400)
        
        result = bookmarks_collection().insert_one({
            'userId': user_id,
            'bookId': book_id,
            'page': page,
            'note': note,
            'createdAt': datetime.now(timezone.utc)
        })
        
        return JsonResponse({
            'id': str(result.inserted_id),
            'page': page,
            'note': note
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@auth_required
def delete_bookmark(request, book_id, bookmark_id):
    """Eliminar marcador"""
    try:
        user_id = request.user_data.get('id')
        result = bookmarks_collection().delete_one({
            '_id': ObjectId(bookmark_id),
            'userId': user_id,
            'bookId': book_id
        })
        
        if result.deleted_count > 0:
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Marcador no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)