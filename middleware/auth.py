"""
Authentication Middleware
"""
from functools import wraps
from bottle import request, abort
import os

def require_auth(func):
    """Decorator for requiring API key authentication"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.getenv('API_KEY_REQUIRED', 'false').lower() == 'true':
            api_key = request.headers.get('X-API-Key')
            valid_keys = os.getenv('API_KEYS', '').split(',')
            
            if not api_key or api_key not in valid_keys:
                abort(401, 'Unauthorized')
        
        return func(*args, **kwargs)
    return wrapper
