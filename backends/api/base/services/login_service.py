# backend/api/base/services/login_service.py
"""
Service layer for login and authentication logic
"""
import logging
from typing import Optional, Dict, Any, Tuple
from django.core.cache import cache
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt
from axes.conf import settings as axes_settings
from axes.handlers.proxy import AxesProxyHandler

from ..constants import LoginMessages, CacheKeys, AppConstants

logger = logging.getLogger(__name__)
User = get_user_model()
axes_handler = AxesProxyHandler()


class LoginService:
    """Service class to handle login logic"""
    
    @staticmethod
    def get_actual_username(username_input: str) -> Optional[str]:
        """
        Convert email to username if needed.
        Returns None if user doesn't exist.
        
        Args:
            username_input: Username or email input from user
            
        Returns:
            Actual username or None if not found
        """
        if not username_input:
            return None
        
        # Check cache first
        cache_key = CacheKeys.get_username_lookup(username_input)
        cached_username = cache.get(cache_key)
        if cached_username:
            return cached_username
        
        # Check if input is email
        if "@" in username_input:
            try:
                user = User.objects.only('username').get(email__iexact=username_input)
                cache.set(cache_key, user.username, AppConstants.CACHE_TIMEOUT)
                return user.username
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None
        
        # Check if username exists
        exists = User.objects.filter(username__iexact=username_input).exists()
        if exists:
            cache.set(cache_key, username_input, AppConstants.CACHE_TIMEOUT)
            return username_input
        
        return None
    
    @staticmethod
    def check_account_status(request, actual_username: Optional[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if account is locked or inactive.
        
        Args:
            request: HTTP request object
            actual_username: The actual username to check
            
        Returns:
            Tuple of (is_locked: bool, error_context: dict)
        """
        if not actual_username:
            return False, {}
        
        # Check cache first
        cache_key = CacheKeys.get_account_status(actual_username)
        cached_status = cache.get(cache_key)
        if cached_status:
            return cached_status
        
        # Check if user is active
        try:
            user = User.objects.only('is_active').get(username=actual_username)
            if not user.is_active:
                result = (True, {
                    'error_message': LoginMessages.ACCOUNT_LOCKED,
                    'is_permanently_blocked': True
                })
                cache.set(cache_key, result, AppConstants.CACHE_TIMEOUT_SHORT)
                return result
        except User.DoesNotExist:
            pass
        
        # Check Axes lock status
        if axes_handler.is_locked(request, {'username': actual_username}):
            result = (True, {
                'error_message': LoginMessages.ACCOUNT_LOCKED,
                'is_axes_blocked': True
            })
            cache.set(cache_key, result, AppConstants.CACHE_TIMEOUT_SHORT)
            return result
        
        # Account is not locked
        result = (False, {})
        cache.set(cache_key, result, AppConstants.CACHE_TIMEOUT_SHORT)
        return result
    
    @staticmethod
    def get_login_error_context(actual_username: Optional[str]) -> Dict[str, Any]:
        """
        Get appropriate error context based on login attempts.
        
        Args:
            actual_username: The actual username
            
        Returns:
            Dictionary with error_message
        """
        if not actual_username:
            return {'error_message': LoginMessages.INVALID_CREDENTIALS}
        
        try:
            # Get failure attempts from Axes
            attempt = AccessAttempt.objects.filter(
                username=actual_username
            ).only('failures_since_start').first()
            
            if attempt:
                failures = attempt.failures_since_start
                limit = axes_settings.AXES_FAILURE_LIMIT
                remaining = max(0, limit - failures)
                
                # Account will be locked
                if remaining <= 0:
                    return {'error_message': LoginMessages.ACCOUNT_LOCKED}
                
                # Warn about remaining attempts
                if failures > 1 and remaining > 0:
                    return {
                        'error_message': LoginMessages.ACCOUNT_WILL_BE_LOCKED.format(remaining)
                    }
        except Exception as e:
            logger.error(f"Error checking attempts for {actual_username}: {e}")
        
        return {'error_message': LoginMessages.INVALID_CREDENTIALS}
    
    @staticmethod
    def clear_user_cache(username: str) -> None:
        """
        Clear all cached data for a user.
        
        Args:
            username: Username to clear cache for
        """
        if not username:
            return
        
        cache_keys = [
            CacheKeys.get_username_lookup(username),
            CacheKeys.get_account_status(username),
        ]
        cache.delete_many(cache_keys)
        
        logger.debug(f"Cleared cache for user: {username}")