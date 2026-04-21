from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import json
import logging

from .db import subscriptions_collection, users_collection
from .decorators import auth_required

logger = logging.getLogger(__name__)

PLANS = {
    'monthly': {
        'name': 'Plan Mensual',
        'price': 3.99,
        'duration_days': 30,
        'features': ['Acceso ilimitado a libros premium', 'Sin anuncios', 'Descargas offline']
    },
    'yearly': {
        'name': 'Plan Anual',
        'price': 20.99,
        'duration_days': 365,
        'features': ['Acceso ilimitado a libros premium', 'Sin anuncios', 'Descargas offline', '2 meses gratis']
    }
}

@require_http_methods(["GET"])
def get_plans(request):
    """Obtener planes de suscripción disponibles"""
    return JsonResponse(PLANS)


@require_http_methods(["GET"])
@auth_required
def get_subscription(request):
    """Obtener suscripción actual del usuario"""
    try:
        user_id = request.user_data.get('id')

        sub = subscriptions_collection().find_one({
            'userId': user_id,
            'status': 'active',
            'expiresAt': {'$gt': datetime.now(timezone.utc)}
        })

        if sub:
            sub['id'] = str(sub['_id'])
            del sub['_id']
            if sub.get('expiresAt'):
                sub['expiresAt'] = sub['expiresAt'].isoformat()
            if sub.get('createdAt'):
                sub['createdAt'] = sub['createdAt'].isoformat()
            return JsonResponse({'active': True, 'subscription': sub})

        return JsonResponse({'active': False, 'subscription': None})
    except Exception as e:
        logger.exception("Error obteniendo suscripción")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def create_subscription(request):
    """Crear una suscripción después del pago"""
    try:
        user_id = request.user_data.get('id')
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        plan_type = data.get('plan', 'monthly')
        payment_id = data.get('paymentId')

        if plan_type not in PLANS:
            return JsonResponse({'error': 'Plan inválido'}, status=400)

        plan = PLANS[plan_type]
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=plan['duration_days'])

        # Cancelar suscripción anterior si existe
        subscriptions_collection().update_many(
            {'userId': user_id, 'status': 'active'},
            {'$set': {'status': 'cancelled', 'cancelledAt': now}}
        )

        # Crear nueva suscripción
        subscription = {
            'userId': user_id,
            'plan': plan_type,
            'planName': plan['name'],
            'price': plan['price'],
            'paymentId': payment_id,
            'status': 'active',
            'createdAt': now,
            'expiresAt': expires_at,
        }

        result = subscriptions_collection().insert_one(subscription)

        # Actualizar usuario como premium
        users_collection().update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'isPremium': True,
                'subscriptionPlan': plan_type,
                'subscriptionExpires': expires_at,
            }}
        )

        response_sub = {
            'id': str(result.inserted_id),
            'userId': user_id,
            'plan': plan_type,
            'planName': plan['name'],
            'price': plan['price'],
            'paymentId': payment_id,
            'status': 'active',
            'createdAt': now.isoformat(),
            'expiresAt': expires_at.isoformat(),
        }

        logger.info("Suscripción creada user=%s plan=%s paymentId=%s",
                    user_id, plan_type, payment_id)
        return JsonResponse({'success': True, 'subscription': response_sub})
    except Exception as e:
        logger.exception("Error creando suscripción")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@auth_required
def cancel_subscription(request):
    """Cancelar suscripción"""
    try:
        user_id = request.user_data.get('id')

        result = subscriptions_collection().update_one(
            {'userId': user_id, 'status': 'active'},
            {'$set': {'status': 'cancelled', 'cancelledAt': datetime.now(timezone.utc)}}
        )

        if result.modified_count == 0:
            return JsonResponse({'error': 'No hay suscripción activa'}, status=404)

        # No quitamos isPremium hasta que expire
        return JsonResponse({'success': True, 'message': 'Suscripción cancelada. Tendrás acceso hasta la fecha de expiración.'})
    except Exception as e:
        logger.exception("Error cancelando suscripción")
        return JsonResponse({'error': str(e)}, status=500)


def check_premium_access(user_id):
    """Verificar si el usuario tiene acceso premium (suscripción activa y no expirada)"""
    if not user_id:
        return False
    try:
        sub = subscriptions_collection().find_one({
            'userId': str(user_id),
            'status': 'active',
            'expiresAt': {'$gt': datetime.now(timezone.utc)}
        })
        return sub is not None
    except Exception:
        logger.exception("Error verificando premium access")
        return False
