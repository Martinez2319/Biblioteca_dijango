import json
import secrets
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from bson import ObjectId
from datetime import datetime, timezone

from .db import users_collection
from .auth_utils import hash_password, check_password, create_token, serialize_user
from .validators import (
    validate_email_format,
    validate_email_domain,
    validate_password_strength,
)

logger = logging.getLogger(__name__)


def send_verification_email(email, token, request):
    """Enviar email de verificacion"""
    verify_url = f"{request.scheme}://{request.get_host()}/verify-email?token={token}"
    try:
        send_mail(
            subject='Verifica tu cuenta - Biblioteca Virtual',
            message=(
                'Bienvenido a Biblioteca Virtual!\n\n'
                'Para completar tu registro, verifica tu email haciendo clic en el '
                'siguiente enlace:\n'
                f'{verify_url}\n\n'
                'Este enlace expira en 24 horas.\n\n'
                'Si no creaste esta cuenta, ignora este mensaje.\n\n'
                'Saludos,\nBiblioteca Virtual'
            ),
            from_email=settings.EMAIL_FROM,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error("Error enviando email de verificacion a %s: %s", email, e)
        return False


@csrf_exempt
@require_http_methods(["POST"])
def validate_signup(request):
    """Endpoint publico para validar en tiempo real los datos del registro.
    El frontend lo llama al perder el foco en los campos email/password.
    Devuelve los resultados de cada regla sin crear usuario."""
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    check_domain = bool(data.get('checkDomain', False))

    result = {
        'email': {'valid': False, 'message': '', 'exists': False, 'domainValid': None},
        'password': {'valid': False, 'message': '', 'checks': {}},
    }

    # Email formato
    if email:
        ok, msg = validate_email_format(email)
        result['email']['valid'] = ok
        result['email']['message'] = msg

        # Si el formato es correcto y el cliente lo pide, validamos dominio
        if ok and check_domain:
            dom_ok, dom_msg = validate_email_domain(email)
            result['email']['domainValid'] = dom_ok
            if not dom_ok:
                result['email']['valid'] = False
                result['email']['message'] = dom_msg

        # Si el formato es correcto, comprobamos si ya esta registrado
        if ok:
            try:
                exists = users_collection().find_one(
                    {'email': email}, {'_id': 1}
                ) is not None
                result['email']['exists'] = exists
                if exists:
                    result['email']['valid'] = False
                    result['email']['message'] = 'Este email ya esta registrado'
            except Exception:
                logger.exception("Error consultando email")

    # Contrasena
    if password:
        ok, msg, checks = validate_password_strength(password)
        result['password']['valid'] = ok
        result['password']['message'] = msg
        result['password']['checks'] = checks

    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    try:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos invalidos'}, status=400)

        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        # 1) Nombre
        if not name:
            return JsonResponse({'error': 'El nombre es requerido'}, status=400)
        if len(name) < 2:
            return JsonResponse({'error': 'El nombre debe tener al menos 2 caracteres'}, status=400)
        if len(name) > 80:
            return JsonResponse({'error': 'El nombre es demasiado largo'}, status=400)

        # 2) Email: formato
        ok_fmt, msg_fmt = validate_email_format(email)
        if not ok_fmt:
            return JsonResponse({'error': msg_fmt}, status=400)

        # 3) Email: dominio (MX lookup)
        ok_dom, msg_dom = validate_email_domain(email)
        if not ok_dom:
            return JsonResponse({'error': msg_dom}, status=400)

        # 4) Contrasena segura
        ok_pw, msg_pw, checks = validate_password_strength(password)
        if not ok_pw:
            return JsonResponse({'error': msg_pw, 'passwordChecks': checks}, status=400)

        # 5) Email ya registrado
        if users_collection().find_one({'email': email}):
            return JsonResponse({'error': 'Este email ya esta registrado'}, status=400)

        # Crear usuario
        verification_token = secrets.token_urlsafe(32)
        user = {
            'name': name,
            'email': email,
            'passwordHash': hash_password(password),
            'role': 'user',
            'emailVerified': False,
            'verificationToken': verification_token,
            'createdAt': datetime.now(timezone.utc)
        }
        result = users_collection().insert_one(user)
        user['_id'] = result.inserted_id

        # Enviar email de verificacion
        email_sent = False
        if settings.EMAIL_HOST_USER:
            email_sent = send_verification_email(email, verification_token, request)

        token = create_token(user['_id'])
        response_data = {
            'success': True,
            'user': serialize_user(user),
            'token': token,
            'emailVerificationSent': email_sent,
        }
        if not email_sent and settings.EMAIL_HOST_USER:
            response_data['warning'] = 'No se pudo enviar el email de verificacion'

        response = JsonResponse(response_data)
        response.set_cookie('token', token, httponly=True, max_age=86400, samesite='Lax')
        return response

    except Exception as e:
        logger.exception("Error en registro")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos invalidos'}, status=400)

        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        user = users_collection().find_one({'email': email})
        if not user or not check_password(password, user.get('passwordHash', '')):
            return JsonResponse({'error': 'Credenciales invalidas'}, status=401)

        token = create_token(user['_id'])

        user_data = serialize_user(user)
        user_data['emailVerified'] = user.get('emailVerified', True)

        response = JsonResponse({'success': True, 'user': user_data, 'token': token})
        response.set_cookie('token', token, httponly=True, max_age=86400, samesite='Lax')
        return response

    except Exception as e:
        logger.exception("Error en login")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def resend_verification_public(request):
    """Reenviar email de verificacion SIN requerir login previo.
    Acepta email en el body. Devuelve respuesta generica para no filtrar
    si el email existe o no."""
    try:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}
        email = (data.get('email') or '').strip().lower()
        if not email:
            return JsonResponse({'error': 'Email requerido'}, status=400)

        user = users_collection().find_one({'email': email})
        # Respuesta generica (no revelar si el email existe)
        generic_ok = JsonResponse({
            'success': True,
            'message': 'Si la cuenta existe y no esta verificada, te enviamos un nuevo correo.'
        })

        if not user or user.get('emailVerified'):
            return generic_ok

        verification_token = secrets.token_urlsafe(32)
        users_collection().update_one(
            {'_id': user['_id']},
            {'$set': {'verificationToken': verification_token}}
        )
        send_verification_email(user['email'], verification_token, request)
        return generic_ok

    except Exception as e:
        logger.exception("Error reenviando verificacion publica")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    response = JsonResponse({'success': True})
    response.delete_cookie('token')
    return response


@require_http_methods(["GET"])
def me(request):
    if not request.user_data:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    # Anadimos isPremium calculado en tiempo real (verifica suscripcion activa
    # no expirada) para que la navbar pueda mostrar el distintivo correcto.
    from .views_subscriptions import check_premium_access
    data = dict(request.user_data)
    data['isPremium'] = check_premium_access(data.get('id'))
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def verify_email(request):
    """Verificar email con token"""
    try:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos invalidos'}, status=400)
        token = data.get('token', '')

        if not token:
            return JsonResponse({'error': 'Token requerido'}, status=400)

        user = users_collection().find_one({'verificationToken': token})

        if not user:
            return JsonResponse({'error': 'Token invalido o expirado'}, status=400)

        if user.get('emailVerified'):
            return JsonResponse({'success': True, 'message': 'Email ya verificado'})

        users_collection().update_one(
            {'_id': user['_id']},
            {
                '$set': {'emailVerified': True},
                '$unset': {'verificationToken': ''}
            }
        )

        return JsonResponse({'success': True, 'message': 'Email verificado correctamente'})

    except Exception as e:
        logger.exception("Error verificando email")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def resend_verification(request):
    """Reenviar email de verificacion"""
    try:
        if not request.user_data:
            return JsonResponse({'error': 'No autenticado'}, status=401)

        user_id = request.user_data.get('id')
        user = users_collection().find_one({'_id': ObjectId(user_id)})

        if not user:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        if user.get('emailVerified'):
            return JsonResponse({'success': True, 'message': 'Email ya verificado'})

        verification_token = secrets.token_urlsafe(32)
        users_collection().update_one(
            {'_id': user['_id']},
            {'$set': {'verificationToken': verification_token}}
        )

        if send_verification_email(user['email'], verification_token, request):
            return JsonResponse({'success': True, 'message': 'Email de verificacion enviado'})
        else:
            return JsonResponse({'error': 'Error al enviar email'}, status=500)

    except Exception as e:
        logger.exception("Error reenviando verificacion")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def debug_session(request):
    """Endpoint publico de diagnostico para ver como llega la peticion
    al backend (cookies, Authorization, resultado del middleware JWT).
    No expone datos sensibles."""
    from .auth_utils import verify_token

    cookies_recv = {k: (v[:10] + '...' if len(v) > 12 else v) for k, v in request.COOKIES.items()}
    raw_token = request.COOKIES.get('token') or ''
    auth_hdr = request.META.get('HTTP_AUTHORIZATION', '')
    header_token = auth_hdr[7:] if auth_hdr.startswith('Bearer ') else ''

    used_token = raw_token or header_token
    decoded = verify_token(used_token) if used_token else None

    info = {
        'host': request.get_host(),
        'scheme': request.scheme,
        'has_cookie_token': bool(raw_token),
        'cookie_token_preview': (raw_token[:15] + '...') if raw_token else None,
        'has_auth_header': bool(header_token),
        'all_cookies': list(cookies_recv.keys()),
        'token_verified_user_id': str(decoded) if decoded else None,
        'request_user_data': request.user_data,
    }
    return JsonResponse(info)
