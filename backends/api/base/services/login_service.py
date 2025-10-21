import logging
from typing import Optional
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils import timezone
from axes.models import AccessAttempt

from backends.api.base.constants import LoginMessages, CacheKeys, AppConstants

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginService:
    """Enhanced service with deactivation logic"""
    
    @staticmethod
    def get_actual_username(username_input: str) -> Optional[str]:
        """Convert email to username or validate username exists"""
        if not username_input:
            return None
        
        username_input = username_input.strip()
        
        # Check cache first
        cache_key = CacheKeys.get_username_lookup(username_input)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None
        
        # Check if input is email
        if "@" in username_input:
            try:
                user = User.objects.only('username').get(email__iexact=username_input)
                actual_username = user.username
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                actual_username = None
        else:
            # Check if username exists
            if User.objects.filter(username__iexact=username_input).exists():
                actual_username = username_input
            else:
                actual_username = None
        
        # Cache result
        cache.set(cache_key, actual_username or "", AppConstants.CACHE_TIMEOUT)
        
        return actual_username
    
    @staticmethod
    def is_user_locked(username: str) -> bool:
        """Check if user has 7+ failures in Axes"""
        if not username:
            return False
        
        try:
            attempt = AccessAttempt.objects.filter(username=username).first()
            if attempt and attempt.failures_since_start >= 7:
                return True
        except Exception as e:
            logger.error(f"Error checking lock status for {username}: {e}")
        
        return False
    
    @staticmethod
    def get_failure_count(username: str) -> int:
        """Get current failure count from Axes"""
        if not username:
            return 0
        
        try:
            attempt = AccessAttempt.objects.filter(username=username).first()
            if attempt:
                return attempt.failures_since_start
        except Exception as e:
            logger.error(f"Error getting failure count for {username}: {e}")
        
        return 0
    
    @staticmethod
    def deactivate_locked_user(username: str, request=None) -> bool:
        """
        Deactivate user when locked by Axes.
        Called when user reaches 7 failures.
        """
        try:
            with transaction.atomic():
                user = User.objects.filter(username=username, is_active=True).first()
                if user:
                    # Prepare deactivation note
                    now = timezone.now()
                    ip_address = request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'
                    note = f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Auto-deactivated after 7 failed login attempts from IP {ip_address}"
                    
                    # Deactivate user
                    user.is_active = False
                    user.save(update_fields=['is_active'])
                    
                    # Log the deactivation note for audit (user model has no 'notes' field)
                    logger.critical(
                        f"SECURITY: User '{username}' deactivated after 7 failed attempts from IP {ip_address} -- note: {note.strip()}"
                    )
                    
                    # Clear cache
                    LoginService.clear_user_cache(username)
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error deactivating user {username}: {e}")
        
        return False
    
    @staticmethod
    def unlock_and_activate_user(username: str, admin_user=None) -> bool:
        """
        Unlock and reactivate user (used by admin).
        - Delete Axes attempts
        - Set is_active = True
        - Reset failure counters
        """
        try:
            with transaction.atomic():
                # 1. Reset Axes attempts
                AccessAttempt.objects.filter(username=username).delete()
                
                # 2. Activate user and reset counters
                user = User.objects.filter(username=username).first()
                if user:
                    user.is_active = True
                    user.failed_login_attempts = 0 # type: ignore
                    user.last_failed_login = None # type: ignore
                    
                    # Add unlock note (logged for audit since user model has no 'notes' field)
                    now = timezone.now()
                    admin_name = admin_user.username if admin_user else 'System'
                    note = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Unlocked and activated by {admin_name}"
                    
                    user.save(update_fields=[
                        'is_active',
                        'failed_login_attempts', 
                        'last_failed_login',
                    ])
                    
                    # 3. Clear cache
                    LoginService.clear_user_cache(username)
                    
                    logger.info(f"User '{username}' unlocked and activated by {admin_name} -- note: {note}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error unlocking user {username}: {e}")
        
        return False
    
    @staticmethod
    def clear_user_cache(username: str) -> None:
        """Clear all cache entries for a user"""
        if not username:
            return
        
        cache_keys = [
            CacheKeys.get_username_lookup(username),
            CacheKeys.get_account_status(username),
            f"user_{username}",
            f"axes_locked_{username}",
        ]
        
        cache.delete_many(cache_keys)
        logger.debug(f"Cleared cache for user: {username}")