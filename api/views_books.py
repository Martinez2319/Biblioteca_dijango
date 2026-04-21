import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone

from .db import books_collection, access_logs_collection, get_collection
from .decorators import admin_required
from .views_subscriptions import check_premium_access

logger = logging.getLogger(__name__)


def purchases_collection():
    return get_collection('purchases')

def reviews_collection():
    return get_collection('reviews')

def process_urls(book):
    """Procesa URLs remotas para libros"""
    if book.get('coverUrl', '').startswith('remote:'):
        filename = book['coverUrl'][7:]
        book['coverUrl'] = f'/api/remote/file/cover/{filename}'
        book['isRemoteCover'] = True
    if book.get('pdfUrl', '').startswith('remote:'):
        filename = book['pdfUrl'][7:]
        book['pdfUrl'] = f'/api/remote/file/pdf/{filename}'
        book['isRemotePdf'] = True
    return book

def serialize_book(book):
    if not book:
        return None
    book['id'] = str(book['_id'])
    book['_id'] = str(book['_id'])

    # Obtener rating promedio
    reviews = list(reviews_collection().find({'bookId': book['id']}))
    if reviews:
        book['averageRating'] = round(sum(r.get('rating', 0) for r in reviews) / len(reviews), 1)
        book['totalReviews'] = len(reviews)
    else:
        book['averageRating'] = 0
        book['totalReviews'] = 0

    return process_urls(book)

def user_has_purchased(user_id, book_id):
    """Verificar si el usuario compró el libro individualmente"""
    if not user_id:
        return False
    purchase = purchases_collection().find_one({
        'userId': str(user_id),
        'bookId': str(book_id),
        'status': 'completed'
    })
    return purchase is not None


def user_has_premium_access(user_data, book_id):
    """Devuelve True si el usuario puede leer el libro premium.
    Es admin, tiene suscripción activa, o compró el libro individualmente."""
    if not user_data:
        return False
    if user_data.get('role') == 'admin':
        return True
    user_id = user_data.get('id')
    if check_premium_access(user_id):
        return True
    if user_has_purchased(user_id, book_id):
        return True
    return False


@require_http_methods(["GET"])
def list_books(request):
    try:
        search = request.GET.get('search', '')
        category = request.GET.get('category', '')
        sort = request.GET.get('sort', 'createdAt')
        price_filter = request.GET.get('priceFilter', '')

        query = {}
        if search:
            query['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'author': {'$regex': search, '$options': 'i'}}
            ]
        if category:
            query['categories'] = category

        if price_filter == 'free':
            query['isPremium'] = {'$ne': True}
        elif price_filter == 'premium':
            query['isPremium'] = True

        sort_field = sort if sort in ['title', 'views', 'createdAt'] else 'createdAt'
        sort_order = 1 if sort == 'title' else -1

        books = list(books_collection().find(query).sort(sort_field, sort_order))
        serialized = [serialize_book(b) for b in books]

        # Si ordenar por rating
        if sort == 'rating':
            serialized.sort(key=lambda x: x.get('averageRating', 0), reverse=True)

        return JsonResponse(serialized, safe=False)
    except Exception as e:
        logger.exception("Error listando libros")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def featured_books(request):
    try:
        books = list(books_collection().find().sort('views', -1).limit(10))
        return JsonResponse([serialize_book(b) for b in books], safe=False)
    except Exception as e:
        logger.exception("Error libros destacados")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def recent_books(request):
    try:
        books = list(books_collection().find().sort('createdAt', -1).limit(10))
        return JsonResponse([serialize_book(b) for b in books], safe=False)
    except Exception as e:
        logger.exception("Error libros recientes")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_book(request, book_id):
    try:
        book = books_collection().find_one({'_id': ObjectId(book_id)})
        if not book:
            return JsonResponse({'error': 'Libro no encontrado'}, status=404)

        serialized = serialize_book(book)

        # Verificar acceso premium (suscripción activa, admin o compra directa)
        if request.user_data and serialized.get('isPremium'):
            user_id = request.user_data.get('id')
            has_subscription = check_premium_access(user_id)
            has_purchased = user_has_purchased(user_id, book_id)
            is_admin = request.user_data.get('role') == 'admin'

            serialized['hasSubscription'] = has_subscription
            serialized['userHasPurchased'] = has_purchased
            serialized['userHasAccess'] = has_subscription or has_purchased or is_admin

        return JsonResponse(serialized)
    except Exception as e:
        logger.exception("Error obteniendo libro")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@admin_required
def create_book(request):
    try:
        data = json.loads(request.body)

        is_premium = data.get('isPremium', False)
        price = float(data.get('price', 0)) if is_premium else 0

        book = {
            'title': data.get('title'),
            'author': data.get('author'),
            'description': data.get('description', ''),
            'categories': data.get('categories', []),
            'tags': data.get('tags', []),
            'coverUrl': data.get('coverUrl'),
            'pdfUrl': data.get('pdfUrl'),
            'content': data.get('content'),
            'isPremium': is_premium,
            'price': price,
            'views': 0,
            'createdAt': datetime.now(timezone.utc)
        }
        result = books_collection().insert_one(book)
        book['_id'] = result.inserted_id

        # Notificar a usuarios si hay sistema de notificaciones
        try:
            from .views_reviews import notify_all_users
            notify_all_users(
                'Nuevo libro disponible',
                f'"{book["title"]}" de {book["author"]} ya está disponible.',
                f'/book/{result.inserted_id}'
            )
        except Exception:
            logger.warning("No se pudo notificar nuevo libro", exc_info=True)

        return JsonResponse(serialize_book(book))
    except Exception as e:
        logger.exception("Error creando libro")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
@admin_required
def update_book(request, book_id):
    try:
        data = json.loads(request.body)
        update_data = {}

        for field in ['title', 'author', 'description', 'categories', 'tags', 'coverUrl', 'pdfUrl', 'content']:
            if field in data:
                update_data[field] = data[field]

        # Campos premium
        if 'isPremium' in data:
            update_data['isPremium'] = data['isPremium']
            update_data['price'] = float(data.get('price', 0)) if data['isPremium'] else 0

        books_collection().update_one({'_id': ObjectId(book_id)}, {'$set': update_data})
        book = books_collection().find_one({'_id': ObjectId(book_id)})
        return JsonResponse(serialize_book(book))
    except Exception as e:
        logger.exception("Error actualizando libro")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@admin_required
def delete_book(request, book_id):
    try:
        books_collection().delete_one({'_id': ObjectId(book_id)})
        return JsonResponse({'success': True})
    except Exception as e:
        logger.exception("Error eliminando libro")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def register_read(request, book_id):
    try:
        book = books_collection().find_one({'_id': ObjectId(book_id)})
        if not book:
            return JsonResponse({'error': 'Libro no encontrado'}, status=404)

        # Incrementar vistas
        books_collection().update_one({'_id': ObjectId(book_id)}, {'$inc': {'views': 1}})

        # Verificar si es premium
        if book.get('isPremium'):
            if not request.user_data:
                return JsonResponse({
                    'allowed': False,
                    'message': 'Inicia sesión para acceder a libros premium.',
                    'isPremium': True,
                    'price': book.get('price', 0)
                })

            user_id = request.user_data.get('id')

            # 1) Admin → acceso libre
            if request.user_data.get('role') == 'admin':
                return JsonResponse({'allowed': True, 'message': 'Acceso como administrador'})

            # 2) Suscripción premium activa → acceso ilimitado a TODOS los libros premium
            if check_premium_access(user_id):
                return JsonResponse({
                    'allowed': True,
                    'message': 'Acceso concedido con suscripción premium',
                    'accessType': 'subscription'
                })

            # 3) Compra individual del libro
            if user_has_purchased(user_id, book_id):
                return JsonResponse({
                    'allowed': True,
                    'message': 'Acceso concedido (libro comprado)',
                    'accessType': 'purchase'
                })

            # Sin acceso premium
            return JsonResponse({
                'allowed': False,
                'message': 'Este libro es premium. Suscríbete o cómpralo individualmente.',
                'isPremium': True,
                'price': book.get('price', 0),
                'canSubscribe': True
            })

        # Usuario autenticado (libro no premium)
        if request.user_data:
            return JsonResponse({'allowed': True, 'message': 'Acceso como usuario registrado'})

        # Usuario invitado - límite de 1 libro
        identifier = request.META.get('REMOTE_ADDR', 'unknown')
        guest_reads = access_logs_collection().count_documents({'identifier': identifier})

        if guest_reads >= 1:
            existing = access_logs_collection().find_one({'identifier': identifier, 'bookId': book_id})
            if existing:
                return JsonResponse({'allowed': True, 'message': 'Continuar leyendo'})
            return JsonResponse({'allowed': False, 'message': 'Límite alcanzado. Regístrate para leer más.'})

        access_logs_collection().insert_one({
            'identifier': identifier,
            'bookId': book_id,
            'timestamp': datetime.now(timezone.utc)
        })
        return JsonResponse({'allowed': True, 'message': 'Acceso concedido'})
    except Exception as e:
        logger.exception("Error registrando lectura")
        return JsonResponse({'error': str(e)}, status=500)

# === COMPRAS DE LIBROS PREMIUM ===

@csrf_exempt
@require_http_methods(["POST"])
def purchase_book(request, book_id):
    """Registrar compra de libro premium (después de pago)"""
    try:
        if not request.user_data:
            return JsonResponse({'error': 'No autenticado'}, status=401)

        user_id = request.user_data.get('id')
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}
        payment_id = data.get('paymentId')

        book = books_collection().find_one({'_id': ObjectId(book_id)})
        if not book:
            return JsonResponse({'error': 'Libro no encontrado'}, status=404)

        if not book.get('isPremium'):
            return JsonResponse({'error': 'Este libro no es premium'}, status=400)

        # Verificar si ya lo compró
        if user_has_purchased(user_id, book_id):
            return JsonResponse({'success': True, 'message': 'Ya tienes acceso a este libro'})

        # Registrar compra
        purchases_collection().insert_one({
            'userId': user_id,
            'bookId': book_id,
            'paymentId': payment_id,
            'amount': book.get('price', 0),
            'status': 'completed',
            'createdAt': datetime.now(timezone.utc)
        })

        return JsonResponse({'success': True, 'message': 'Compra registrada'})
    except Exception as e:
        logger.exception("Error registrando compra")
        return JsonResponse({'error': str(e)}, status=500)
