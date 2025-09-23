# backend/tenancy/signals.py - SECURE VERSION
from django.core.signals import request_finished
from django.db import connections
from django.conf import settings
from django.core.cache import cache
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from axes.signals import user_locked_out
import logging

logger = logging.getLogger('backend.tenancy')

# Import the actual User model to avoid type issues
from .models.user import User


@receiver(user_locked_out)
def handle_axes_lockout(sender, request, username, ip_address, **kwargs):
    """When axes locks out a user, deactivate them immediately"""
    try:
        user = User.objects.get(username=username)
        if user.is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])
            logger.warning(f"SECURITY: User {username} deactivated due to axes lockout from IP {ip_address}")
            
            # Add note about the lockout
            from django.utils import timezone
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            current_notes = user.notes or ""
            user.notes = f"{current_notes}\n[{timestamp}] Auto-blocked: Too many failed login attempts from IP {ip_address}".strip()
            user.save(update_fields=['notes'])
    except User.DoesNotExist:
        logger.warning(f"Axes lockout for non-existent user: {username}")


@receiver(user_logged_in)
def handle_successful_login(sender, request, user, **kwargs):
    """Reset failed attempts ONLY for active users on successful login"""
    # CRITICAL: Only reset if user is active (not blocked)
    # Type check to ensure it's our custom User model
    if not isinstance(user, User):
        return
        
    if user.is_active:
        # Reset failed attempts in our model
        if hasattr(user, 'failed_login_attempts') and user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.last_failed_login = None
            user.save(update_fields=['failed_login_attempts', 'last_failed_login'])
            logger.info(f"Reset failed attempts for active user {user.username}")
            
        # Axes will auto-reset its own counters because AXES_RESET_ON_SUCCESS = True
    else:
        # This should never happen if backend is working correctly
        logger.error(f"WARNING: Blocked user {user.username} somehow logged in! This should not happen!")


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    """Track failed login attempts"""
    username = credentials.get('username')
    if username:
        try:
            user = User.objects.get(username=username)
            
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Update last failed login time
            from django.utils import timezone
            user.last_failed_login = timezone.now()
            
            user.save(update_fields=['failed_login_attempts', 'last_failed_login'])
            
            # Log the failure
            logger.info(f"Failed login attempt #{user.failed_login_attempts} for user {username}")
            
            # Check if user should be blocked based on attempt count
            from axes.conf import settings as axes_settings
            if user.failed_login_attempts >= axes_settings.AXES_FAILURE_LIMIT and user.is_active:
                # User reached limit - deactivate them
                user.is_active = False
                user.save(update_fields=['is_active'])
                logger.warning(f"SECURITY: User {username} auto-blocked after {user.failed_login_attempts} failed attempts")
                
        except User.DoesNotExist:
            logger.info(f"Failed login attempt for non-existent user: {username}")


# Database connection management
class DBConnectionManager:
    """Manage DB connections efficiently"""
    
    CACHE_PREFIX = 'study_db_usage_'
    BATCH_SIZE = 10
    
    @classmethod
    def release_unused_dbs(cls, sender, **kwargs):
        """Release unused study DBs"""
        for conn in connections.all():
            conn.close_if_unusable_or_obsolete()
        
        study_aliases = [
            alias for alias in connections.databases.keys()
            if alias != 'default' and alias.startswith(settings.STUDY_DB_PREFIX)
        ]
        
        for alias in study_aliases[:cls.BATCH_SIZE]:
            usage_key = f"{cls.CACHE_PREFIX}{alias}"
            if not cache.get(usage_key):
                try:
                    if alias in connections:
                        connections[alias].close()
                    del connections.databases[alias]
                    logger.debug(f"Released: {alias}")
                except Exception as e:
                    logger.error(f"Error releasing {alias}: {e}")
            else:
                cache.delete(usage_key)

request_finished.connect(DBConnectionManager.release_unused_dbs)