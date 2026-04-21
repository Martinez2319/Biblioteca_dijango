from django.utils.deprecation import MiddlewareMixin
from .auth_utils import verify_token, get_user_by_id

class JWTAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.user_data = None
        
        token = request.COOKIES.get('token')
        if not token:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if token:
            user_id = verify_token(token)
            if user_id:
                request.user_data = get_user_by_id(user_id)
