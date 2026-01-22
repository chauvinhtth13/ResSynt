# backends/audit_logs/utils/rate_limiter.py
"""
BASE Rate Limiter - Shared across all studies

Rate limiting for audit log operations with email alerting

SECURITY:
- Protects against brute force attacks
- Logs suspicious activity with user-agent
- Async email alerts via Celery (throttled)
"""
from django.core.cache import cache
from django.http import HttpResponse
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def rate_limit(key_prefix: str, max_requests: int = 10, window: int = 60):
    """
    Rate limit decorator
    
    ENHANCED: Added user-agent logging for security analysis
    
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
            # Build cache key with IP and user ID
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = f'rate_limit:{key_prefix}:{ip}:{user_id}'
            
            # Atomic increment with get_or_set
            count = cache.get(cache_key, 0)
            
            if count >= max_requests:
                # Log with user-agent for security analysis
                user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:200]
                logger.warning(
                    "RATE LIMIT EXCEEDED: ip=%s user=%s count=%d window=%ds path=%s ua=%s",
                    ip, user_id, count, window, request.path, user_agent
                )
                
                # Send async alert email via Celery (throttled - once per 5 min)
                alert_key = f'alert_sent:{cache_key}'
                if not cache.get(alert_key):
                    _send_rate_limit_alert(request, ip, user_id, count, window)
                    cache.set(alert_key, True, 300)  # Don't spam alerts
                
                return HttpResponse(
                    'Quá nhiều yêu cầu. Vui lòng thử lại sau.',
                    status=429,
                    headers={'Retry-After': str(window)}  # RFC 6585 compliance
                )
            
            # Increment counter atomically
            cache.set(cache_key, count + 1, window)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def _send_rate_limit_alert(request, ip, user_id, count, window):
    """
    Send rate limit alert email asynchronously
    
    Separated for cleaner code and testability
    """
    try:
        from backends.tenancy.tasks import send_security_alert
        
        send_security_alert.delay(
            alert_type='rate_limit_exceeded',
            details={
                'username': request.user.username if request.user.is_authenticated else 'Anonymous',
                'ip_address': ip,
                'endpoint': request.path,
                'count': f"{count} requests in {window} seconds",
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],
                'timestamp': datetime.now().isoformat(),
            }
        )
        logger.info("Queued alert email for rate limit: %s", ip)
    except ImportError:
        logger.debug("Celery tasks not available, skipping alert email")
    except Exception as e:
        logger.error("Failed to queue alert email: %s", e)
