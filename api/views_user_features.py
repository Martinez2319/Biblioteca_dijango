import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone

from .db import get_collection, books_collection
from .decorators import auth_required

def safe_isoformat(val):
    """Convierte a ISO string de forma segura (acepta datetime o string)"""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


def favorites_collection():
    return get_collection('favorites')

def reading_progress_collection():
    return get_collection('reading_progress')

def reading_history_collection():
    return get_collection('reading_history')

# ==================== FAVORITOS ====================

@require_http_methods(["GET"])
@auth_required
def get_favorites(request):
    """Obtener lista de favoritos del usuario"""
    try:
        user_id = request.user_data.get('id')
        favorites = list(favorites_collection().find({'userId': user_id}))
        
        # Obtener datos de los libros
        book_ids = [ObjectId(f['bookId']) for f in favorites]
        books = list(books_collection().find({'_id': {'$in': book_ids}}))
        
        # Serializar
        result = []
        for book in books:
            book['id'] = str(book['_id'])
            book['_id'] = str(book['_id'])
            fav = next((f for f in favorites if f['bookId'] == book['id']), None)
            book['favoritedAt'] = safe_isoformat(fav.get('createdAt')) if fav else None
            result.append(book)
        
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def toggle_favorite(request, book_id):
    """Agregar o quitar de favoritos"""
    try:
        user_id = request.user_data.get('id')
        
        existing = favorites_collection().find_one({
            'userId': user_id,
            'bookId': book_id
        })
        
        if existing:
            favorites_collection().delete_one({'_id': existing['_id']})
            return JsonResponse({'favorited': False, 'message': 'Eliminado de favoritos'})
        else:
            favorites_collection().insert_one({
                'userId': user_id,
                'bookId': book_id,
                'createdAt': datetime.now(timezone.utc)
            })
            return JsonResponse({'favorited': True, 'message': 'Agregado a favoritos'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
@auth_required
def check_favorite(request, book_id):
    """Verificar si un libro está en favoritos"""
    try:
        user_id = request.user_data.get('id')
        existing = favorites_collection().find_one({
            'userId': user_id,
            'bookId': book_id
        })
        return JsonResponse({'favorited': existing is not None})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==================== PROGRESO DE LECTURA ====================

@require_http_methods(["GET"])
@auth_required
def get_progress(request, book_id):
    """Obtener progreso de lectura de un libro"""
    try:
        user_id = request.user_data.get('id')
        progress = reading_progress_collection().find_one({
            'userId': user_id,
            'bookId': book_id
        })
        
        if progress:
            return JsonResponse({
                'currentPage': progress.get('currentPage', 1),
                'totalPages': progress.get('totalPages', 1),
                'percentage': progress.get('percentage', 0),
                'lastRead': safe_isoformat(progress.get('updatedAt'))
            })
        return JsonResponse({'currentPage': 1, 'totalPages': 1, 'percentage': 0, 'lastRead': None})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def save_progress(request, book_id):
    """Guardar progreso de lectura"""
    try:
        user_id = request.user_data.get('id')
        data = json.loads(request.body)
        
        current_page = data.get('currentPage', 1)
        total_pages = data.get('totalPages', 1)
        percentage = round((current_page / total_pages) * 100, 1) if total_pages > 0 else 0
        
        reading_progress_collection().update_one(
            {'userId': user_id, 'bookId': book_id},
            {'$set': {
                'currentPage': current_page,
                'totalPages': total_pages,
                'percentage': percentage,
                'updatedAt': datetime.now(timezone.utc)
            },
            '$setOnInsert': {
                'createdAt': datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        # También actualizar historial
        update_history(user_id, book_id)
        
        return JsonResponse({
            'success': True,
            'currentPage': current_page,
            'percentage': percentage
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
@auth_required
def get_all_progress(request):
    """Obtener progreso de todos los libros del usuario"""
    try:
        user_id = request.user_data.get('id')
        progress_list = list(reading_progress_collection().find({'userId': user_id}))
        
        # Obtener datos de los libros
        book_ids = [ObjectId(p['bookId']) for p in progress_list]
        books = {str(b['_id']): b for b in books_collection().find({'_id': {'$in': book_ids}})}
        
        result = []
        for p in progress_list:
            book = books.get(p['bookId'])
            if book:
                result.append({
                    'bookId': p['bookId'],
                    'title': book.get('title'),
                    'author': book.get('author'),
                    'coverUrl': book.get('coverUrl'),
                    'currentPage': p.get('currentPage', 1),
                    'totalPages': p.get('totalPages', 1),
                    'percentage': p.get('percentage', 0),
                    'lastRead': safe_isoformat(p.get('updatedAt'))
                })
        
        # Ordenar por último leído
        result.sort(key=lambda x: x['lastRead'] or '', reverse=True)
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==================== HISTORIAL ====================

def update_history(user_id, book_id):
    """Actualizar historial de lectura (función interna)"""
    reading_history_collection().update_one(
        {'userId': user_id, 'bookId': book_id},
        {'$set': {
            'lastReadAt': datetime.now(timezone.utc)
        },
        '$inc': {'readCount': 1},
        '$setOnInsert': {
            'firstReadAt': datetime.now(timezone.utc)
        }},
        upsert=True
    )

@require_http_methods(["GET"])
@auth_required
def get_history(request):
    """Obtener historial de lectura del usuario"""
    try:
        user_id = request.user_data.get('id')
        limit = int(request.GET.get('limit', 20))
        
        history = list(reading_history_collection().find(
            {'userId': user_id}
        ).sort('lastReadAt', -1).limit(limit))
        
        # Obtener datos de los libros
        book_ids = [ObjectId(h['bookId']) for h in history]
        books = {str(b['_id']): b for b in books_collection().find({'_id': {'$in': book_ids}})}
        
        result = []
        for h in history:
            book = books.get(h['bookId'])
            if book:
                result.append({
                    'bookId': h['bookId'],
                    'title': book.get('title'),
                    'author': book.get('author'),
                    'coverUrl': book.get('coverUrl'),
                    'lastReadAt': safe_isoformat(h.get('lastReadAt')),
                    'firstReadAt': safe_isoformat(h.get('firstReadAt')),
                    'readCount': h.get('readCount', 1)
                })
        
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@auth_required
def clear_history(request):
    """Limpiar historial del usuario"""
    try:
        user_id = request.user_data.get('id')
        reading_history_collection().delete_many({'userId': user_id})
        return JsonResponse({'success': True, 'message': 'Historial eliminado'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

