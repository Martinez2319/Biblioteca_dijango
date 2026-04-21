import json
import requests
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from datetime import datetime, timezone
import gzip
from io import BytesIO

from .db import remote_sources_collection
from .decorators import admin_required

def get_api_key():
    return settings.REMOTE_API_KEY

def verify_api_key(request):
    key = request.headers.get('X-Api-Key') or request.GET.get('apiKey')
    return key == get_api_key()

def get_source(online_only=False):
    query = {'apiKey': get_api_key()}
    if online_only:
        query['isOnline'] = True
    return remote_sources_collection().find_one(query)

# === ENDPOINTS PARA PC REMOTO ===

@csrf_exempt
@require_http_methods(["POST"])
def register_pc(request):
    if not verify_api_key(request):
        return JsonResponse({'error': 'API key inválida'}, status=401)
    
    try:
        data = json.loads(request.body)
        url = data.get('url')
        name = data.get('name', 'Mi PC')

        if not url:
            return JsonResponse({'error': 'URL requerida'}, status=400)

        source = get_source()
        if source:
            remote_sources_collection().update_one(
                {'_id': source['_id']},
                {'$set': {'url': url, 'name': name, 'isOnline': True, 'lastSeen': datetime.now(timezone.utc)}}
            )
        else:
            remote_sources_collection().insert_one({
                'url': url,
                'name': name,
                'apiKey': get_api_key(),
                'isOnline': True,
                'lastSeen': datetime.now(timezone.utc),
                'createdAt': datetime.now(timezone.utc)
            })

        return JsonResponse({'success': True, 'message': 'PC registrado'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def heartbeat(request):
    if not verify_api_key(request):
        return JsonResponse({'error': 'API key inválida'}, status=401)
    
    try:
        source = get_source()
        if source:
            remote_sources_collection().update_one(
                {'_id': source['_id']},
                {'$set': {'lastSeen': datetime.now(timezone.utc), 'isOnline': True}}
            )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def disconnect(request):
    if not verify_api_key(request):
        return JsonResponse({'error': 'API key inválida'}, status=401)
    
    try:
        source = get_source()
        if source:
            remote_sources_collection().update_one(
                {'_id': source['_id']},
                {'$set': {'isOnline': False}}
            )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# === ENDPOINTS PARA ADMIN ===

@require_http_methods(["GET"])
@admin_required
def status(request):
    try:
        source = get_source()
        if not source:
            return JsonResponse({'connected': False, 'message': 'No hay PC configurado'})

        # Verificar si está online (última vez visto hace menos de 60s)
        if source.get('lastSeen'):
            diff = (datetime.now(timezone.utc) - source['lastSeen'].replace(tzinfo=timezone.utc)).total_seconds()
            if diff >= 60:
                remote_sources_collection().update_one(
                    {'_id': source['_id']},
                    {'$set': {'isOnline': False}}
                )
                source['isOnline'] = False

        return JsonResponse({
            'connected': source.get('isOnline', False),
            'name': source.get('name'),
            'url': source.get('url'),
            'lastSeen': source.get('lastSeen').isoformat() if source.get('lastSeen') else None
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
@admin_required
def list_files(request):
    try:
        source = get_source(online_only=True)
        if not source:
            return JsonResponse({'error': 'PC no conectado'}, status=404)

        response = requests.get(
            f"{source['url']}/files",
            headers={'X-Api-Key': get_api_key()},
            timeout=10
        )
        return JsonResponse(response.json())
    except Exception as e:
        return JsonResponse({'error': 'No se pudo conectar con el PC'}, status=500)

# === PROXY DE ARCHIVOS CON STREAMING Y GZIP ===

@require_http_methods(["GET"])
def proxy_file(request, file_type, filename):
    """Proxy optimizado con streaming progresivo y compresión GZIP"""
    if file_type not in ['pdf', 'cover']:
        return JsonResponse({'error': 'Tipo inválido'}, status=400)

    try:
        source = get_source(online_only=True)
        if not source:
            return JsonResponse({'error': 'PC no conectado'}, status=404)

        # Streaming progresivo con chunks
        def stream_file():
            with requests.get(
                f"{source['url']}/file/{file_type}/{filename}",
                headers={'X-Api-Key': get_api_key()},
                stream=True,
                timeout=60
            ) as r:
                r.raise_for_status()
                # Chunks de 64KB para mejor rendimiento
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk

        # Determinar content-type
        content_type = 'application/pdf' if file_type == 'pdf' else 'image/jpeg'
        if filename.lower().endswith('.png'):
            content_type = 'image/png'
        elif filename.lower().endswith('.webp'):
            content_type = 'image/webp'

        # Verificar si el cliente acepta GZIP
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        use_gzip = 'gzip' in accept_encoding and file_type != 'pdf'  # No comprimir PDFs (ya están comprimidos)

        if use_gzip:
            # Comprimir respuesta con GZIP
            def gzip_stream():
                buffer = BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=6) as gz:
                    for chunk in stream_file():
                        gz.write(chunk)
                        if buffer.tell() > 32768:  # Flush cada 32KB
                            buffer.seek(0)
                            yield buffer.read()
                            buffer.seek(0)
                            buffer.truncate()
                buffer.seek(0)
                yield buffer.read()

            response = StreamingHttpResponse(gzip_stream(), content_type=content_type)
            response['Content-Encoding'] = 'gzip'
        else:
            response = StreamingHttpResponse(stream_file(), content_type=content_type)

        response['Cache-Control'] = 'public, max-age=3600'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Security-Policy'] = "frame-ancestors 'self'"
        
        # Para PDFs, agregar header de disposición inline
        if file_type == 'pdf':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response

    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'Timeout al conectar con el PC'}, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': 'No se pudo obtener el archivo'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)