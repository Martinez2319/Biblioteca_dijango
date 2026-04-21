import json
import secrets
from datetime import datetime, timezone, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings

from .db import users_collection, get_collection
from .auth_utils import hash_password
from .validators import validate_password_strength

def password_resets_collection():
    return get_collection('password_resets')

@csrf_exempt
@require_http_methods(["POST"])
def request_reset(request):
    """Solicitar recuperación de contraseña"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'error': 'Email requerido'}, status=400)

        user = users_collection().find_one({'email': email})
        if not user:
            # No revelar si el email existe o no (seguridad)
            return JsonResponse({'success': True, 'message': 'Si el email existe, recibirás un enlace de recuperación.'})

        # Generar token único
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Guardar token en DB
        password_resets_collection().delete_many({'email': email})  # Eliminar tokens anteriores
        password_resets_collection().insert_one({
            'email': email,
            'token': token,
            'expires_at': expires_at,
            'used': False
        })

        # Construir enlace
        reset_url = f"{request.scheme}://{request.get_host()}/reset-password?token={token}"

        # Enviar email
        try:
            send_mail(
                subject='Recuperar contraseña - Biblioteca Virtual',
                message=f'''Hola,

Recibimos una solicitud para restablecer tu contraseña.

Haz clic en el siguiente enlace para crear una nueva contraseña:
{reset_url}

Este enlace expira en 1 hora.

Si no solicitaste este cambio, ignora este mensaje.

Saludos,
Biblioteca Virtual''',
                from_email=settings.EMAIL_FROM,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error enviando email: {e}")
            return JsonResponse({'error': 'Error al enviar el email. Verifica la configuración.'}, status=500)

        return JsonResponse({'success': True, 'message': 'Si el email existe, recibirás un enlace de recuperación.'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def reset_password(request):
    """Restablecer contraseña con token"""
    try:
        data = json.loads(request.body)
        token = data.get('token', '')
        new_password = data.get('password', '')

        if not token or not new_password:
            return JsonResponse({'error': 'Token y contraseña requeridos'}, status=400)

        if len(new_password) < 8:
            return JsonResponse({'error': 'La contrasena debe tener al menos 8 caracteres'}, status=400)

        ok_pw, msg_pw, checks = validate_password_strength(new_password)
        if not ok_pw:
            return JsonResponse({'error': msg_pw, 'passwordChecks': checks}, status=400)

        # Buscar token válido
        reset = password_resets_collection().find_one({
            'token': token,
            'used': False
        })

        if not reset:
            return JsonResponse({'error': 'Token inválido o expirado'}, status=400)

        # Verificar expiración
        expires_at = reset['expires_at']
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > expires_at:
            return JsonResponse({'error': 'El enlace ha expirado. Solicita uno nuevo.'}, status=400)

        # Actualizar contraseña
        users_collection().update_one(
            {'email': reset['email']},
            {'$set': {'passwordHash': hash_password(new_password)}}
        )

        # Marcar token como usado
        password_resets_collection().update_one(
            {'_id': reset['_id']},
            {'$set': {'used': True}}
        )

        return JsonResponse({'success': True, 'message': 'Contraseña actualizada correctamente.'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def verify_token(request):
    """Verificar si un token es válido"""
    token = request.GET.get('token', '')
    
    if not token:
        return JsonResponse({'valid': False})

    reset = password_resets_collection().find_one({
        'token': token,
        'used': False
    })

    if not reset:
        return JsonResponse({'valid': False})

    expires_at = reset['expires_at']
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        return JsonResponse({'valid': False})

    return JsonResponse({'valid': True, 'email': reset['email']})