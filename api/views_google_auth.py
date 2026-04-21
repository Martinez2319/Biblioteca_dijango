"""Emergent-managed Google OAuth integration.

Flujo:
 1) El usuario pulsa "Continuar con Google" en /register o /login.
    El browser redirige a https://auth.emergentagent.com/?redirect=<origin>/auth/google/callback
 2) Emergent devuelve al usuario a <origin>/auth/google/callback#session_id=XYZ
 3) La pagina del callback toma el session_id del fragmento y lo envia
    por POST a /api/auth/google
 4) Este endpoint llama a Emergent para validar el session_id, recupera
    los datos del usuario (email, name) -> con eso garantizamos que el
    correo pertenece a una cuenta de Google real-,  busca o crea el
    usuario en Mongo y emite el JWT "token" cookie que ya usa el resto
    de la app.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH. El redirect se deriva en el frontend con
window.location.origin.
"""

import json
import logging
from datetime import datetime, timezone

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth_utils import create_token, serialize_user
from .db import users_collection

logger = logging.getLogger(__name__)

EMERGENT_SESSION_DATA_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)


@csrf_exempt
@require_http_methods(["POST"])
def google_auth(request):
    """Intercambia un session_id de Emergent por una sesion local (JWT cookie)."""
    try:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos invalidos'}, status=400)

        session_id = (data.get('session_id') or '').strip()
        if not session_id:
            return JsonResponse(
                {'error': 'Falta session_id de Google'}, status=400
            )

        # 1) Validar el session_id con Emergent y obtener datos del usuario
        try:
            emergent_res = requests.get(
                EMERGENT_SESSION_DATA_URL,
                headers={'X-Session-ID': session_id},
                timeout=10,
            )
        except requests.RequestException as e:
            logger.exception("Fallo conectando a Emergent Auth")
            return JsonResponse(
                {'error': 'No se pudo contactar al servicio de Google'},
                status=502,
            )

        if emergent_res.status_code != 200:
            logger.warning(
                "Emergent session-data rechazado: %s %s",
                emergent_res.status_code, emergent_res.text[:200],
            )
            return JsonResponse(
                {'error': 'La cuenta de Google no pudo ser verificada. '
                          'Asegurate de usar una cuenta de Google existente.'},
                status=401,
            )

        info = emergent_res.json() or {}
        email = (info.get('email') or '').strip().lower()
        name = (info.get('name') or '').strip() or email.split('@')[0]
        picture = info.get('picture') or ''

        if not email:
            return JsonResponse(
                {'error': 'La cuenta de Google no devolvio email valido'},
                status=400,
            )

        # 2) Buscar o crear el usuario en nuestra base
        users = users_collection()
        user = users.find_one({'email': email})

        if user is None:
            # Nuevo usuario registrado via Google -> email ya validado
            new_user = {
                'name': name,
                'email': email,
                'role': 'user',
                'emailVerified': True,
                'authProvider': 'google',
                'picture': picture,
                'createdAt': datetime.now(timezone.utc),
            }
            result = users.insert_one(new_user)
            new_user['_id'] = result.inserted_id
            user = new_user
            created = True
        else:
            # Usuario existente -> marcarlo como verificado y enlazar Google
            update_fields = {
                'emailVerified': True,
                'authProvider': user.get('authProvider') or 'google',
            }
            if picture and not user.get('picture'):
                update_fields['picture'] = picture
            users.update_one({'_id': user['_id']}, {'$set': update_fields})
            user.update(update_fields)
            created = False

        # 3) Emitir JWT "token" cookie tal como hace /api/auth/login
        token = create_token(user['_id'])
        response_data = {
            'success': True,
            'created': created,
            'user': serialize_user(user),
            'token': token,
        }
        response = JsonResponse(response_data)
        response.set_cookie(
            'token', token, httponly=True, max_age=86400, samesite='Lax'
        )
        return response

    except Exception as e:
        logger.exception("Error en google_auth")
        return JsonResponse({'error': str(e)}, status=500)
