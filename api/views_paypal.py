import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from datetime import datetime, timezone

from .db import donations_collection
from .decorators import admin_required

def get_paypal_url():
    if settings.PAYPAL_MODE == 'sandbox':
        return 'https://api-m.sandbox.paypal.com'
    return 'https://api-m.paypal.com'

def get_paypal_token():
    response = requests.post(
        f'{get_paypal_url()}/v1/oauth2/token',
        data='grant_type=client_credentials',
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json().get('access_token')

@require_http_methods(["GET"])
def config(request):
    return JsonResponse({
        'clientId': settings.PAYPAL_CLIENT_ID or None,
        'mode': settings.PAYPAL_MODE,
        'currency': 'USD'
    })

@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount', 0))
        message = data.get('message', '')

        if amount <= 0:
            return JsonResponse({'error': 'Monto inválido'}, status=400)

        # Modo mock si no hay credenciales
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET:
            mock_order_id = str(int(datetime.now().timestamp() * 1000))
            donations_collection().insert_one({
                'amount': amount,
                'message': message,
                'paypalOrderId': mock_order_id,
                'status': 'pending',
                'createdAt': datetime.now(timezone.utc)
            })
            return JsonResponse({'orderId': mock_order_id, 'mode': 'mock'})

        token = get_paypal_token()
        response = requests.post(
            f'{get_paypal_url()}/v2/checkout/orders',
            json={
                'intent': 'CAPTURE',
                'purchase_units': [{'amount': {'currency_code': 'USD', 'value': f'{amount:.2f}'}}]
            },
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        )
        order_data = response.json()

        donations_collection().insert_one({
            'amount': amount,
            'message': message,
            'paypalOrderId': order_data['id'],
            'status': 'pending',
            'createdAt': datetime.now(timezone.utc)
        })

        return JsonResponse({'orderId': order_data['id'], 'mode': 'live'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def capture_order(request, order_id):
    try:
        # Modo mock
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET:
            donations_collection().update_one(
                {'paypalOrderId': order_id},
                {'$set': {'status': 'completed'}}
            )
            return JsonResponse({'status': 'completed', 'mode': 'mock'})

        token = get_paypal_token()
        response = requests.post(
            f'{get_paypal_url()}/v2/checkout/orders/{order_id}/capture',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        )
        capture_data = response.json()

        status = 'completed' if capture_data.get('status') == 'COMPLETED' else 'failed'
        donations_collection().update_one(
            {'paypalOrderId': order_id},
            {'$set': {'status': status}}
        )

        return JsonResponse({'status': status, 'details': capture_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
@admin_required
def list_donations(request):
    try:
        donations = list(donations_collection().find().sort('createdAt', -1))
        for d in donations:
            d['id'] = str(d['_id'])
            d['_id'] = str(d['_id'])
            if d.get('createdAt'):
                d['createdAt'] = d['createdAt'].isoformat()
        return JsonResponse(donations, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
