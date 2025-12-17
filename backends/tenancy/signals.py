"""
Tenancy Signals - Authentication, study lifecycle, and membership sync.
"""
import logging
from datetime import timedelta
from typing import Any, Optional

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.db.models.signals import post_migrate, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from allauth.account.signals import user_logged_in as allauth_logged_in
from allauth.account.signals import user_logged_out as allauth_logged_out
from axes.signals import user_locked_out

logger = logging.getLogger(__name__)


# =============================================================================
# Authentication Signals
# =============================================================================

@receiver(allauth_logged_in)
def handle_allauth_login(request, user, **kwargs):
    """
    Handle successful login via allauth.
    
    Security measures:
    - Session regeneration (prevent session fixation)
    - Reset axes attempts
    - Clear cached blocked status
    """
    try:
        # Regenerate session key (prevent session fixation)
        if hasattr(request, 'session'):
            request.session.cycle_key()
        
        # Reset axes attempts
        from axes.utils import reset
        reset(username=user.username)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Clear cached blocked status
        cache.delete_many([
            f'axes:{user.username}',
            f'axes:user:{user.pk}',
            f'user_blocked_{user.username}',
        ])
        
        # Log login (minimal info)
        logger.info(f"User logged in: {user.username}")
        
    except Exception as e:
        logger.error(f"Login handler error: {type(e).__name__}")


@receiver(allauth_logged_out)
def handle_allauth_logout(request, user, **kwargs):
    """Handle logout via allauth."""
    if not user:
        return
    
    try:
        from backends.tenancy.utils import TenancyUtils
        TenancyUtils.clear_user_cache(user)
        
        # Clear study session
        if hasattr(request, 'session'):
            for key in ('current_study', 'current_study_code', 'current_study_db'):
                request.session.pop(key, None)
        
        logger.info(f"User logged out: {user.username}")
        
    except Exception as e:
        logger.error(f"Logout handler error: {type(e).__name__}")


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    """
    Handle failed login attempt.
    
    - Check if user is manually blocked
    - Log attempt for security monitoring
    """
    username = credentials.get('username', 'unknown')
    
    try:
        from backends.tenancy.models import User
        
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                # User manually blocked - log but don't count as axes attempt
                logger.warning(f"Blocked user login attempt: {username}")
                return
        except User.DoesNotExist:
            pass
        
        # Log failed attempt (IP logged by axes)
        logger.warning(f"Failed login attempt: {username}")
        
    except Exception as e:
        logger.error(f"Failed login handler error: {type(e).__name__}")


@receiver(user_locked_out)
def handle_axes_lockout(request, username, ip_address, **kwargs):
    """
    Handle axes lockout event.
    
    - Update user record
    - Send admin alert
    """
    try:
        from backends.tenancy.models import User
        from django.core.mail import mail_admins
        
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        server_name = getattr(settings, 'SERVER_NAME', 'Application')
        
        logger.warning(f"User locked out: {username} from {ip_address}")
        
        # Update user record if exists
        try:
            user = User.objects.get(username=username)
            user.notes = f"{user.notes or ''}\n[{timestamp}] Lockout from {ip_address}".strip()
            user.save(update_fields=['notes'])
            
            # Send alert for existing user
            _send_lockout_alert(username, ip_address, timestamp, server_name, exists=True)
            
        except User.DoesNotExist:
            # Send alert for non-existent user (potential attack)
            _send_lockout_alert(username, ip_address, timestamp, server_name, exists=False)
            
    except Exception as e:
        logger.error(f"Lockout handler error: {type(e).__name__}")


def _send_lockout_alert(username: str, ip: str, timestamp: str, server: str, exists: bool):
    """Send lockout alert to admins."""
    try:
        from django.core.mail import mail_admins
        
        if exists:
            subject = 'Security Alert: User Locked Out'
            message = (
                f"User locked out after multiple failed login attempts.\n\n"
                f"User: {username}\n"
                f"IP: {ip}\n"
                f"Time: {timestamp}\n"
                f"Server: {server}\n\n"
                f"To unlock: python manage.py axes_reset {username}"
            )
        else:
            subject = 'Security Alert: Invalid User Login Attempts'
            message = (
                f"Multiple login attempts for non-existent user.\n"
                f"This may indicate a brute-force attack.\n\n"
                f"Username: {username} (DOES NOT EXIST)\n"
                f"IP: {ip}\n"
                f"Time: {timestamp}\n"
                f"Server: {server}\n\n"
                f"Consider blocking IP: {ip}"
            )
        
        mail_admins(subject=subject, message=message, fail_silently=True)
        
    except Exception as e:
        logger.error(f"Failed to send lockout alert: {type(e).__name__}")


# =============================================================================
# Study Lifecycle Signals
# =============================================================================

@receiver(post_save, sender='tenancy.Study')
def auto_create_study_roles(sender: Any, instance: Any, created: bool, **kwargs) -> None:
    """Create groups and permissions when study is created."""
    if not created:
        return
    
    try:
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        result = StudyRoleManager.initialize_study(instance.code, force=False)
        
        if 'error' not in result:
            logger.info(
                f"Study {instance.code} initialized: "
                f"{result.get('groups_created', 0)} groups, "
                f"{result.get('permissions_assigned', 0)} permissions"
            )
            
    except Exception as e:
        logger.error(f"Failed to initialize study {instance.code}: {type(e).__name__}")


@receiver(post_migrate)
def sync_study_permissions_after_migrate(sender: AppConfig, **kwargs) -> None:
    """Sync permissions after migrations for study apps."""
    if not _is_study_app(sender):
        return
    
    study_code = _extract_study_code(sender)
    if not study_code:
        return
    
    try:
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        result = StudyRoleManager.assign_permissions(study_code, force=True)
        
        assigned = result.get('permissions_assigned', 0)
        removed = result.get('permissions_removed', 0)
        
        if assigned > 0 or removed > 0:
            logger.info(f"Study {study_code} permissions synced: +{assigned}, -{removed}")
            
    except Exception as e:
        logger.error(f"Failed to sync permissions for {study_code}: {type(e).__name__}")


# =============================================================================
# Membership Signals
# =============================================================================

@receiver(post_save, sender='tenancy.StudyMembership')
def sync_groups_on_membership_change(sender, instance, created, **kwargs):
    """Sync user groups when membership changes."""
    try:
        from backends.tenancy.utils import TenancyUtils
        
        if instance.user:
            TenancyUtils.sync_user_groups(instance.user)
            
            if created:
                logger.info(f"Membership created: {instance.user.username} in {instance.study.code}")
                
    except Exception as e:
        logger.error(f"Membership sync error: {type(e).__name__}")


@receiver(pre_delete, sender='tenancy.StudyMembership')
def sync_groups_on_membership_delete(sender, instance, **kwargs):
    """Clear cache when membership is deleted."""
    try:
        from backends.tenancy.utils import TenancyUtils
        
        if instance.user:
            TenancyUtils.clear_user_cache(instance.user)
            logger.info(f"Membership removed: {instance.user.username} from {instance.study.code}")
            
    except Exception as e:
        logger.error(f"Membership delete error: {type(e).__name__}")


# =============================================================================
# Helper Functions
# =============================================================================

def _is_study_app(app_config: AppConfig) -> bool:
    """Check if app is a study app."""
    return (
        hasattr(app_config, 'name') and 
        app_config.name.startswith('backends.studies.study_')
    )


def _extract_study_code(app_config: AppConfig) -> Optional[str]:
    """Extract study code from app name."""
    if not hasattr(app_config, 'name'):
        return None
    
    parts = app_config.name.split('.')
    if len(parts) < 3:
        return None
    
    app_name = parts[-1]
    if not app_name.startswith('study_'):
        return None
    
    return app_name.replace('study_', '', 1).upper() or None


# =============================================================================
# Cleanup Tasks
# =============================================================================

def cleanup_expired_sessions():
    """
    Clean up expired sessions.
    
    Should be called via Celery beat or management command.
    """
    try:
        from django.contrib.sessions.models import Session
        
        deleted = Session.objects.filter(
            expire_date__lt=timezone.now()
        ).delete()[0]
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired sessions")
            
    except Exception as e:
        logger.error(f"Session cleanup error: {type(e).__name__}")


def cleanup_old_access_logs(days: int = 30):
    """
    Clean up old axes access logs.
    
    Args:
        days: Keep logs for this many days
    """
    try:
        from axes.models import AccessLog
        
        cutoff = timezone.now() - timedelta(days=days)
        deleted = AccessLog.objects.filter(attempt_time__lt=cutoff).delete()[0]
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old access logs")
            
    except Exception as e:
        logger.error(f"Access log cleanup error: {type(e).__name__}")