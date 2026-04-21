from functools import wraps
from django.http import JsonResponse

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user_data or request.user_data.get('role') != 'admin':
            return JsonResponse({'error': 'Acceso denegado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user_data:
            return JsonResponse({'error': 'No autenticado'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
