from rest_framework import authentication
from rest_framework import exceptions
from django.utils import timezone
import hashlib
from core.models import APIToken


class APITokenAuthentication(authentication.BaseAuthentication):
    """
    Custom token authentication for API requests.
    Tokens are passed in the Authorization header as: Token <token>
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Token '):
            return None
        
        token = auth_header.split(' ')[1] if len(auth_header.split(' ')) > 1 else None
        
        if not token:
            return None
        
        # Hash the provided token to compare with stored hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            api_token = APIToken.objects.get(token=token_hash, is_active=True)
        except APIToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid or revoked API token.')
        
        # Check if token is expired
        if api_token.is_expired():
            raise exceptions.AuthenticationFailed('API token has expired.')
        
        # Update last used timestamp
        api_token.last_used_at = timezone.now()
        api_token.save(update_fields=['last_used_at'])
        
        return (api_token.user, None)


