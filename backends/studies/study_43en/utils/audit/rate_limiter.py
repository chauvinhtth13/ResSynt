# backends/studies/study_43en/utils/rate_limiter.py

from django.core.cache import cache
from django.core.mail import mail_admins
from django.http import HttpResponse
from django.conf import settings
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def rate_limit(key_prefix: str, max_requests: int = 10, window: int = 60):
    """
    Rate limit decorator
    ✅ ENHANCED: Added email alerting
    
    Args:
        key_prefix: Prefix for cache key
        max_requests: Max requests allowed in window
        window: Time window in seconds
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
                
                # ✅ NEW: Send alert email (throttled)
                alert_key = f'alert_sent:{cache_key}'
                if not cache.get(alert_key):  # Only send once per 5 minutes
                    try:
                        server_name = getattr(settings, 'SERVER_NAME', 'ReSYNC')
                        mail_admins(
                            subject=f'🚨 SECURITY ALERT: Rate Limit Exceeded',
                            message=(
                                f"A user has exceeded rate limits.\n"
                                f"\n"
                                f"Details:\n"
                                f"  IP Address: {ip}\n"
                                f"  User ID:    {user_id}\n"
                                f"  Username:   {request.user.username if request.user.is_authenticated else 'Anonymous'}\n"
                                f"  Endpoint:   {request.path}\n"
                                f"  Method:     {request.method}\n"
                                f"  Attempts:   {count} requests in {window} seconds\n"
                                f"  Time:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"  Server:     {server_name}\n"
                                f"\n"
                                f"Action Taken:\n"
                                f"  - Request blocked with HTTP 429\n"
                                f"  - User will be rate-limited for {window} seconds\n"
                                f"\n"
                                f"Recommended Actions:\n"
                                f"  1. Review user activity\n"
                                f"  2. Check if this is legitimate traffic\n"
                                f"  3. Consider blocking IP if malicious\n"
                            ),
                            fail_silently=True
                        )
                        logger.info(f"Alert email sent for rate limit: {ip}")
                        cache.set(alert_key, True, 300)  # Don't spam alerts
                    except Exception as e:
                        logger.error(f"Failed to send alert email: {e}")
                
                return HttpResponse(
                    'Quá nhiều yêu cầu. Vui lòng thử lại sau.',
                    status=429
                )
            
            # Increment counter
            cache.set(cache_key, count + 1, window)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator