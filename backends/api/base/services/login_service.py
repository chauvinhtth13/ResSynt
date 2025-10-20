# backend/api/base/services/login_service.py - OPTIMIZED
"""
Service layer for login and authentication logic
"""
import logging
from typing import Optional, Dict, Any, Tuple
from django.core.cache import cache
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt
from django.conf import settings

from backends.api.base.constants import LoginMessages, CacheKeys, AppConstants

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginService:
    """Service class to handle login logic with lockout checking"""
    
    @staticmethod
    def get_actual_username(username_input: str) -> Optional[str]:
        """
        Get actual username from input (email or username).
        Uses cache for performance.
        """
        if not username_input:
            return None
        
        username_input = username_input.strip()
        
        # Check cache first
        cache_key = CacheKeys.get_username_lookup(username_input)
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Check if input is email
        if "@" in username_input:
            try:
                user = User.objects.only('username').get(email__iexact=username_input)
                cache.set(cache_key, user.username, AppConstants.CACHE_TIMEOUT)
                return user.username
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None
        
        # Check if username exists
        try:
            user = User.objects.only('username').get(username__iexact=username_input)
            cache.set(cache_key, user.username, AppConstants.CACHE_TIMEOUT)
            return user.username
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def check_lockout_status(username: str, request=None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user is locked out.
        Returns (is_locked, context_dict)
        
        Context dict contains:
        - is_locked: bool
        - error_message: str
        - form_disabled: bool
        - remaining_attempts: int (if not locked)
        """
        if not username:
            return False, {}
        
        # Check cache first
        cache_key = CacheKeys.get_account_status(username)
        cached_status = cache.get(cache_key)
        
        if cached_status and cached_status.get('is_locked'):
            return True, {
                'is_locked': True,
                'error_message': LoginMessages.ACCOUNT_LOCKED,
                'form_disabled': True,
            }
        
        # Check database - user active status
        try:
            user = User.objects.only('is_active', 'username').get(username=username)
            if not user.is_active:
                return True, {
                    'is_locked': True,
                    'error_message': LoginMessages.ACCOUNT_LOCKED,
                    'form_disabled': True,
                }
        except User.DoesNotExist:
            return False, {}
        
        # Check Axes attempts
        failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        
        attempt_count = AccessAttempt.objects.filter(
            username=username,
        ).count()
        
        if attempt_count >= failure_limit:
            # User is locked
            lock_info = {
                'is_locked': True,
                'attempt_count': attempt_count,
            }
            
            # Cache the lock status
            cache.set(cache_key, lock_info, timeout=3600)
            
            return True, {
                'is_locked': True,
                'error_message': LoginMessages.ACCOUNT_LOCKED,
                'form_disabled': True,
            }
        
        # Not locked - return remaining attempts
        remaining = failure_limit - attempt_count
        
        return False, {
            'is_locked': False,
            'remaining_attempts': remaining,
        }
    
    @staticmethod
    def check_account_status(request, actual_username: Optional[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Legacy method - calls check_lockout_status
        """
        if actual_username is None:
            return False, {}
        return LoginService.check_lockout_status(actual_username, request)
    
    @staticmethod
    def get_remaining_attempts(username: str) -> int:
        """Get number of remaining login attempts"""
        if not username:
            return 0
        
        failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        
        attempt_count = AccessAttempt.objects.filter(
            username=username,
        ).count()
        
        return max(0, failure_limit - attempt_count)
    
    @staticmethod
    def clear_user_cache(username: str):
        """Clear all cache entries for user"""
        if not username:
            return
        
        cache.delete_many([
            CacheKeys.get_username_lookup(username),
            CacheKeys.get_account_status(username),
        ])
        
        logger.debug(f"Cleared cache for user: {username}")
    
    @staticmethod
    def record_failed_attempt(request, username: str):
        """
        Record a failed login attempt.
        This is handled by Axes middleware, but can be called manually if needed.
        """
        from axes.handlers.proxy import AxesProxyHandler
        
        handler = AxesProxyHandler()
        handler.user_login_failed(
            request=request,
            credentials={'username': username}
        )
        
        logger.info(f"Recorded failed attempt for: {username}")