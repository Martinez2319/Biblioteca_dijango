import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone

from .db import get_collection, books_collection, users_collection
from .decorators import auth_required, admin_required

def reviews_collection():
    return get_collection('reviews')

def notifications_collection():
    return get_collection('notifications')

# ==================== RESEÑAS ====================

@require_http_methods(["GET"])
def get_reviews(request, book_id):
    """Obtener reseñas de un libro"""
    try:
        reviews = list(reviews_collection().find({'bookId': book_id}).sort('createdAt', -1))
        
        # Obtener nombres de usuarios
        user_ids = [ObjectId(r['userId']) for r in reviews]
        users = {str(u['_id']): u for u in users_collection().find({'_id': {'$in': user_ids}})}
        
        result = []
        for r in reviews:
            user = users.get(r['userId'], {})
            result.append({
                'id': str(r['_id']),
                'userId': r['userId'],
                'userName': user.get('name', 'Usuario'),
                'rating': r.get('rating', 5),
                'comment': r.get('comment', ''),
                'createdAt': r.get('createdAt').isoformat() if r.get('createdAt') else None
            })
        
        # Calcular promedio
        avg_rating = sum(r['rating'] for r in result) / len(result) if result else 0
        
        return JsonResponse({
            'reviews': result,
            'averageRating': round(avg_rating, 1),
            'totalReviews': len(result)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def create_review(request, book_id):
    """Crear o actualizar reseña"""
    try:
        user_id = request.user_data.get('id')
        data = json.loads(request.body)
        
        rating = int(data.get('rating', 5))
        comment = data.get('comment', '').strip()
        
        if rating < 1 or rating > 5:
            return JsonResponse({'error': 'Rating debe ser entre 1 y 5'}, status=400)
        
        # Verificar si ya tiene reseña
        existing = reviews_collection().find_one({'userId': user_id, 'bookId': book_id})
        
        if existing:
            reviews_collection().update_one(
                {'_id': existing['_id']},
                {'$set': {'rating': rating, 'comment': comment, 'updatedAt': datetime.now(timezone.utc)}}
            )
            return JsonResponse({'success': True, 'message': 'Reseña actualizada'})
        else:
            reviews_collection().insert_one({
                'userId': user_id,
                'bookId': book_id,
                'rating': rating,
                'comment': comment,
                'createdAt': datetime.now(timezone.utc)
            })
            return JsonResponse({'success': True, 'message': 'Reseña creada'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@auth_required
def delete_review(request, book_id):
    """Eliminar reseña propia"""
    try:
        user_id = request.user_data.get('id')
        result = reviews_collection().delete_one({'userId': user_id, 'bookId': book_id})
        
        if result.deleted_count > 0:
            return JsonResponse({'success': True, 'message': 'Reseña eliminada'})
        return JsonResponse({'error': 'Reseña no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==================== NOTIFICACIONES ====================

@require_http_methods(["GET"])
@auth_required
def get_notifications(request):
    """Obtener notificaciones del usuario"""
    try:
        user_id = request.user_data.get('id')
        notifs = list(notifications_collection().find({'userId': user_id}).sort('createdAt', -1).limit(50))
        
        result = []
        for n in notifs:
            result.append({
                'id': str(n['_id']),
                'title': n.get('title', ''),
                'message': n.get('message', ''),
                'link': n.get('link', ''),
                'read': n.get('read', False),
                'createdAt': n.get('createdAt').isoformat() if n.get('createdAt') else None
            })
        
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def mark_notification_read(request, notif_id):
    """Marcar notificación como leída"""
    try:
        user_id = request.user_data.get('id')
        notifications_collection().update_one(
            {'_id': ObjectId(notif_id), 'userId': user_id},
            {'$set': {'read': True}}
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def mark_all_read(request):
    """Marcar todas las notificaciones como leídas"""
    try:
        user_id = request.user_data.get('id')
        notifications_collection().update_many(
            {'userId': user_id, 'read': False},
            {'$set': {'read': True}}
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Función helper para crear notificaciones (usar desde otras vistas)
def create_notification(user_id, title, message, link=''):
    """Crear una notificación para un usuario"""
    notifications_collection().insert_one({
        'userId': user_id,
        'title': title,
        'message': message,
        'link': link,
        'read': False,
        'createdAt': datetime.now(timezone.utc)
    })

def notify_all_users(title, message, link=''):
    """Notificar a todos los usuarios"""
    users = users_collection().find({}, {'_id': 1})
    for user in users:
        create_notification(str(user['_id']), title, message, link)