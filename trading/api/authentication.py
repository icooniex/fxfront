from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from trading.models import BotAPIKey


def require_bot_api_key(view_func):
    """
    Decorator to validate master Bot API key from request header.
    This allows the MT5 bot system to access all accounts with a single key.
    """
    @wraps(view_func)
    @csrf_exempt  # API endpoints don't use CSRF tokens
    def wrapper(request, *args, **kwargs):
        # Get API key from Authorization header (Bearer token format)
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid or missing API key. Use: Authorization: Bearer <key>'
            }, status=401)
        
        api_key = auth_header.split('Bearer ')[1].strip()
        
        try:
            # Find active API key
            bot_key = BotAPIKey.objects.get(
                key=api_key,
                is_active=True
            )
            
            # Update last used timestamp
            bot_key.last_used = timezone.now()
            bot_key.save(update_fields=['last_used'])
            
            # Mark request as bot-authenticated
            request.is_bot_authenticated = True
            request.bot_api_key = bot_key
            
            # Call the actual view
            return view_func(request, *args, **kwargs)
            
        except BotAPIKey.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid or inactive API key'
            }, status=401)
    
    return wrapper
