# backend/api/base/lockout.py - OPTIMIZED VERSION
"""
Custom Axes lockout handler - Shows lockout message on login page
"""
import logging
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.db import models

from .constants import LoginMessages, CacheKeys

logger = logging.getLogger(__name__)
User = get_user_model()


def custom_lockout_handler(request, credentials, *args, **kwargs):
    """
    Axes lockout handler.
    MUST return None (Axes requirement).
    Just logs and marks as locked.
    """
    import logging
    from django.core.cache import cache
    from django.contrib.auth import get_user_model
    
    logger = logging.getLogger(__name__)
    User = get_user_model()
    
    username = credentials.get('username')
    
    if not username:
        logger.error("Lockout handler: No username")
        return None
    
    try:
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Mark as locked in cache
        from backends.api.base.constants import CacheKeys
        cache_key = CacheKeys.get_account_status(username)
        cache.set(cache_key, {
            'is_locked': True,
            'locked_at': str(__import__('django.utils.timezone').utils.timezone.now()),
            'ip_address': ip_address
        }, timeout=3600)
        
        # Optional: Deactivate user
        try:
            user = User.objects.filter(username=username, is_active=True).first()
            if user:
                user.is_active = False
                user.save()
                logger.warning(f"User deactivated: {username}")
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
        
        logger.critical(f"LOCKOUT: {username} from {ip_address}")
        
    except Exception as e:
        logger.error(f"Lockout handler error: {e}", exc_info=True)
    
    # CRITICAL: Must return None (Axes requirement)
    return None


def is_user_locked(username: str, request=None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if user is locked out.
    Fast check using cache + Axes database.
    
    Args:
        username: Username to check
        request: Optional request object for IP-based checking
        
    Returns:
        Tuple of (is_locked, lock_info)
    """
    if not username:
        return False, None
    
    # Check cache first (fastest)
    cache_key = CacheKeys.get_account_status(username)
    cached_status = cache.get(cache_key)
    
    if cached_status and cached_status.get('is_locked'):
        return True, cached_status
    
    # Check Axes AccessAttempt
    from axes.models import AccessAttempt
    from django.conf import settings
    
    failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
    
    # Get recent attempts
    attempts = AccessAttempt.objects.filter(
        username=username,
    ).order_by('-attempt_time')[:failure_limit]
    
    if len(attempts) >= failure_limit:
        # Check if user is locked
        # AccessAttempt.get_data may be either a callable or an attribute (and may not be a dict),
        # so handle both cases safely.
        recent_failures = 0
        for a in attempts:
            get_data_attr = getattr(a, "get_data", None)
            if callable(get_data_attr):
                data = get_data_attr()
            else:
                data = get_data_attr
            if isinstance(data, dict):
                success = data.get('success', False)
            else:
                # If data isn't a dict, treat as failure (safe default)
                success = False
            if not success:
                recent_failures += 1

        if recent_failures >= failure_limit:
            lock_info = {
                'is_locked': True,
                'attempt_count': recent_failures,
                'last_attempt': attempts[0].attempt_time.isoformat() if attempts else None
            }
            
            # Cache the lock status
            cache.set(cache_key, lock_info, timeout=3600)
            
            return True, lock_info
    
    return False, None


def get_remaining_attempts(username: str) -> int:
    """
    Get number of remaining login attempts before lockout.
    
    Args:
        username: Username to check
        
    Returns:
        Number of remaining attempts (0 if locked)
    """
    if not username:
        return 0
    
    from axes.models import AccessAttempt
    from django.conf import settings
    
    failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
    
    # Count recent failures
    recent_failures = AccessAttempt.objects.filter(
        username=username,
    ).count()
    
    remaining = max(0, failure_limit - recent_failures)
    
    return remaining