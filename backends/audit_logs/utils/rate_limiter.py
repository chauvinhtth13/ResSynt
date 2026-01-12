# backends/audit_logs/utils/rate_limiter.py
"""
BASE Rate Limiter - Shared across all studies

Rate limiting for audit log operations with email alerting
"""
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def rate_limit(key_prefix: str, max_requests: int = 10, window: int = 60):
    """
    Rate limit decorator
    
    ENHANCED: Added email alerting
    
    Args:
        key_prefix: Prefix for cache key
        max_requests: Max requests allowed in window
        window: Time window in seconds
    
    Example:
        @rate_limit('audit_update', max_requests=10, window=60)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Build cache key
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = f'rate_limit:{key_prefix}:{ip}:{user_id}'
            
            # Get current count
            count = cache.get(cache_key, 0)
            
            if count >= max_requests:
                logger.warning(
                    f"🚨 RATE LIMIT EXCEEDED: {ip} {user_id} "
                    f"({count} requests in {window}s)"
                )
                
                # Send async alert email via Celery (throttled)
                alert_key = f'alert_sent:{cache_key}'
                if not cache.get(alert_key):  # Only send once per 5 minutes
                    try:
                        from backends.tenancy.tasks import send_security_alert
                        
                        send_security_alert.delay(
                            alert_type='rate_limit_exceeded',
                            details={
                                'username': request.user.username if request.user.is_authenticated else 'Anonymous',
                                'ip_address': ip,
                                'endpoint': request.path,
                                'count': f"{count} requests in {window} seconds",
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            }
                        )
                        logger.info(f"✓ Queued alert email for rate limit: {ip}")
                        cache.set(alert_key, True, 300)  # Don't spam alerts
                    except Exception as e:
                        logger.error(f"Failed to queue alert email: {e}")
                
                return HttpResponse(
                    'Quá nhiều yêu cầu. Vui lòng thử lại sau.',
                    status=429
                )
            
            # Increment counter
            cache.set(cache_key, count + 1, window)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
