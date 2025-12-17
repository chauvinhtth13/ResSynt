# backend/tenancy/signals.py - Complete rewrite for allauth + axes

from django.apps import AppConfig
from django.conf import settings
from config.settings import env
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.db import connections
from django.db.models.signals import post_migrate, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from typing import Any, Optional
import logging

from allauth.account.signals import user_logged_in as allauth_logged_in
from allauth.account.signals import user_logged_out as allauth_logged_out
from axes.signals import user_locked_out

logger = logging.getLogger(__name__)


# ==========================================
# ALLAUTH SIGNALS (PRIMARY AUTH HANDLER)
# ==========================================

@receiver(allauth_logged_in)
def handle_allauth_login(request, user, **kwargs):
    """
    Handle successful login via allauth
    Reset axes attempts on successful login
    🔒 SECURITY FIX: Added session regeneration to prevent session fixation
    """
    try:
        # 🔒 CRITICAL: Regenerate session key to prevent session fixation attack
        if hasattr(request, 'session'):
            request.session.cycle_key()
        
        # Reset axes attempts for this user
        from axes.utils import reset
        reset(username=user.username)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Track login IP
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        logger.info(
            f"User {user.username} logged in via allauth from {ip_address}"
        )
        
        # Clear any cached blocked status
        cache_keys = [
            f'axes:{user.username}',
            f'axes:user:{user.pk}',
            f'user_blocked_{user.username}',
        ]
        cache.delete_many(cache_keys)
        
    except Exception as e:
        logger.error(f"Error handling allauth login for {user.username}: {e}")


@receiver(allauth_logged_out)
def handle_allauth_logout(request, user, **kwargs):
    """Handle logout via allauth"""
    if user:
        try:
            # Clear user's cache
            from backends.tenancy.utils import TenancyUtils
            TenancyUtils.clear_user_cache(user)
            
            # Clear session data
            if hasattr(request, 'session'):
                request.session.pop('current_study', None)
                request.session.pop('current_study_code', None)
                request.session.pop('current_study_db', None)
            
            logger.info(f"User {user.username} logged out via allauth")
            
        except Exception as e:
            logger.error(f"Error handling logout for {user.username}: {e}")


# ==========================================
# FAILED LOGIN HANDLING
# ==========================================

@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    """
    Handle failed login attempt - Compatible with axes 8.0.0
    Check if user is manually blocked (is_active=False)
    """
    username = credentials.get('username', 'unknown')
    
    try:
        from backends.tenancy.models import User
        
        # Check if user exists and is manually blocked
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                # User is manually blocked - don't let axes count this
                logger.warning(
                    f"Blocked user '{username}' attempted login from "
                    f"{request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'}"
                )
                
                # Add note to user record
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                user.notes = f"{user.notes}\n[{timestamp}] Login attempt while blocked".strip()
                user.save(update_fields=['notes'])
                
                # Don't process further - user is permanently blocked
                return
        except User.DoesNotExist:
            pass
        
        # Let axes handle the failed attempt counting
        # Axes listens to the same signal so we just log it
        ip_address = request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'
        logger.warning(
            f"Failed login attempt for '{username}' from {ip_address}"
        )
        
    except Exception as e:
        logger.error(f"Error handling failed login for '{username}': {e}")


# ==========================================
# AXES LOCKOUT SIGNAL
# ==========================================

@receiver(user_locked_out)
def handle_axes_lockout(request, username, ip_address, **kwargs):
    """
    Handle axes lockout event
    ✅ ENHANCED: Using Celery for async email alerts
    """
    try:
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.warning(
            f"AXES LOCKOUT: User '{username}' locked out from IP {ip_address}"
        )
        
        # Update user record to track lockout
        from backends.tenancy.models import User
        from backends.tenancy.tasks import send_security_alert
        
        try:
            user = User.objects.get(username=username)
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            user.notes = (
                f"{user.notes}\n[{timestamp}] Axes lockout from IP {ip_address}"
            ).strip()
            user.save(update_fields=['notes'])
            
            # ✅ Send async email alert via Celery
            send_security_alert.delay(
                alert_type='user_lockout',
                details={
                    'username': username,
                    'ip_address': ip_address,
                    'timestamp': timestamp,
                }
            )
            logger.info(f"✓ Queued alert email for lockout: {username}")
                
        except User.DoesNotExist:
            # Log attempt for non-existent user
            logger.info(f"Lockout attempt for non-existent user: {username}")
            
            # ✅ Send async alert for non-existent user (potential attack)
            send_security_alert.delay(
                alert_type='invalid_user_attempt',
                details={
                    'username': username,
                    'ip_address': ip_address,
                    'timestamp': timestamp,
                }
            )
            logger.info(f"✓ Queued alert email for non-existent user: {username}")
            
    except Exception as e:
        logger.error(f"Error handling axes lockout: {e}")



        
# ==========================================
# STUDY ACCESS TRACKING
# ==========================================

def track_study_access_signal(user, study):
    """
    Track when user accesses a study
     FIXED: Use correct field names
    """
    from backends.tenancy.models.user import User
    
    try:
        cache_key = f'study_access_{user.pk}_{study.pk}'
        last_tracked = cache.get(cache_key)
        
        now = timezone.now()
        
        # Only update every 5 minutes to reduce database writes
        if not last_tracked or (now - last_tracked).seconds > 300:
            #  FIXED: Sử dụng field _id để lưu ID của study
            User.objects.filter(pk=user.pk).update(
                last_study_accessed_id=study.pk,  #  Đúng field name
                last_study_accessed_at=now
            )
            
            cache.set(cache_key, now, timeout=300)
            logger.debug(f"Updated study access: user {user.pk} -> study {study.code}")
            
    except Exception as e:
        logger.error(f"Error tracking study access: {e}", exc_info=True)

# ==========================================
# DATABASE CONNECTION MANAGEMENT
# ==========================================

class DatabaseConnectionManager:
    """Helper class for database connection management"""
    
    @staticmethod
    def cleanup_idle_connections():
        """Clean up idle study database connections"""
        cleaned = 0
        
        try:
            study_aliases = [
                alias for alias in list(connections.databases.keys())
                if alias != 'default' and alias.startswith(settings.STUDY_DB_PREFIX)
            ]
            
            for alias in study_aliases:
                try:
                    conn_wrapper = connections[alias]
                    
                    if hasattr(conn_wrapper, 'connection') and conn_wrapper.connection is not None:
                        if hasattr(conn_wrapper, 'close_if_unusable_or_obsolete'):
                            conn_wrapper.close_if_unusable_or_obsolete()
                            cleaned += 1
                            
                except Exception as e:
                    logger.error(f"Error cleaning connection {alias}: {e}")
            
            if cleaned > 0:
                logger.debug(f"Cleaned {cleaned} idle database connection(s)")
                
        except Exception as e:
            logger.error(f"Error in cleanup_idle_connections: {e}")
        
        return cleaned


# ==========================================
# CACHE MANAGEMENT
# ==========================================

def clear_user_cache(user):
    """Clear all cached data for a user"""
    try:
        from backends.tenancy.utils import TenancyUtils
        cleared = TenancyUtils.clear_user_cache(user)
        logger.debug(f"Cleared {cleared} cache key(s) for user {user.pk}")
        return cleared
    except Exception as e:
        logger.error(f"Error clearing user cache: {e}")
        return 0


def clear_study_cache(study):
    """Clear all cached data for a study"""
    try:
        from backends.tenancy.utils import TenancyUtils
        cleared = TenancyUtils.clear_study_cache(study)
        logger.debug(f"Cleared {cleared} cache key(s) for study {study.pk}")
        return cleared
    except Exception as e:
        logger.error(f"Error clearing study cache: {e}")
        return 0


# ==========================================
# UPDATED: STUDY DATABASE AUTO-CREATION
# ==========================================

@receiver(post_save, sender='tenancy.Study')
def auto_create_study_database(sender, instance, created, **kwargs):
    """
    Automatically create database when Study is created/activated
    Improved with better error handling and logging
    """
    # Check if we should create database
    should_create = False
    action = None
    
    if created:
        should_create = True
        action = "created"
    else:
        # Check if reactivated from archived
        try:
            old = sender.objects.get(pk=instance.pk)
            if old.status == instance.Status.ARCHIVED and \
               instance.status in [instance.Status.ACTIVE, instance.Status.PLANNING]:
                should_create = True
                action = "reactivated"
        except sender.DoesNotExist:
            pass
    
    if not should_create:
        return
    
    db_name = instance.db_name
    
    logger.info("=" * 70)
    logger.info(f"AUTO-CREATING DATABASE FOR STUDY {instance.code}")
    logger.info("=" * 70)
    
    try:
        from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
        
        # Check if database exists
        if DatabaseStudyCreator.database_exists(db_name):
            logger.info(f"Database '{db_name}' already exists")
            
            # Ensure schema exists
            from backends.tenancy.db_loader import study_db_manager
            if study_db_manager.ensure_schema_exists(db_name):
                logger.info(f"Schema verified for {db_name}")
        else:
            # Create new database
            logger.info(f"Creating new database '{db_name}'...")
            
            success, message = DatabaseStudyCreator.create_study_database(db_name)
            
            if not success:
                logger.error(f"Failed to create database: {message}")
                return
            
            logger.info(f"Database created: {message}")
            
            # Ensure schema
            from backends.tenancy.db_loader import study_db_manager
            study_db_manager.ensure_schema_exists(db_name)
        
        # Register database dynamically
        _register_database_dynamically(instance)
        
        # Initialize roles
        _auto_initialize_roles(instance)
        
        # Log success and next steps
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"STUDY {instance.code} DATABASE READY")
        logger.info("=" * 70)
        logger.info(f"Database: {db_name}")
        logger.info(f"Status: {instance.status}")
        logger.info("")
        logger.info("Next Steps:")
        logger.info(f"  1. Create folder structure:")
        logger.info(f"     python manage.py create_study_structure {instance.code}")
        logger.info(f"  2. Restart Django server")
        logger.info(f"  3. Run migrations:")
        logger.info(f"     python manage.py migrate --database {db_name}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"ERROR IN AUTO-CREATE DATABASE")
        logger.error("=" * 70)
        logger.error(f"Study: {instance.code}")
        logger.error(f"Database: {db_name}")
        logger.error(f"Error: {e}")
        logger.error("=" * 70, exc_info=True)


def _register_database_dynamically(study):
    """
    Dynamically register database in Django's connections
    UPDATED: Better logging
    """
    db_name = study.db_name
    
    try:
        from django.db import connections
        from config.settings import DatabaseConfig
        
        # Check if already registered
        if db_name in connections.databases:
            logger.debug(f"Database {db_name} already registered")
            return
        
        # Get config
        db_config = DatabaseConfig.get_study_db_config(db_name, env)
        
        # Register in Django
        connections.databases[db_name] = db_config
        
        # Register in study_db_manager
        from backends.tenancy.db_loader import study_db_manager
        study_db_manager.add_study_db(db_name)
        
        logger.debug(f"Registered database: {db_name}")
        
    except Exception as e:
        logger.error(f"Error registering database {db_name}: {e}", exc_info=True)


def _auto_initialize_roles(study):
    """
    Auto-initialize study roles and permissions
    UPDATED: Better logging
    """
    try:
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        logger.debug(f"Initializing roles for study {study.code}...")
        
        result = StudyRoleManager.initialize_study(
            study.code,
            force=False
        )
        
        if 'error' in result:
            logger.warning(f"Could not initialize roles: {result['error']}")
        else:
            logger.debug(
                f"Roles initialized: "
                f"{result.get('groups_created', 0)} groups, "
                f"{result.get('permissions_assigned', 0)} permissions"
            )
        
    except Exception as e:
        logger.warning(f"Could not initialize roles: {e}")



# ==========================================
# STUDY ROLE MANAGEMENT SIGNALS
# ==========================================

@receiver(post_save, sender='tenancy.Study')
def auto_create_study_roles(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """
    Automatically create groups and assign permissions when a new study is created
    """
    if not created:
        return
    
    from backends.tenancy.utils.role_manager import StudyRoleManager
    
    study_code = instance.code
    
    try:
        result = StudyRoleManager.initialize_study(study_code, force=False)
        
        if 'error' not in result:
            logger.info(
                f"Auto-initialized study {study_code}: "
                f"Created {result.get('groups_created', 0)} groups, "
                f"assigned {result.get('permissions_assigned', 0)} permissions"
            )
        
    except Exception as e:
        logger.error(
            f"Failed to auto-create roles for study {study_code}: {e}",
            exc_info=True
        )


@receiver(post_migrate)
def sync_study_permissions_after_migrate(sender: AppConfig, **kwargs: Any) -> None:
    """
    Automatically sync permissions after migrations for study apps
    """
    if not _is_study_app(sender):
        return
    
    study_code = _extract_study_code_from_app(sender)
    if not study_code:
        logger.warning(f"Could not extract study code from app: {sender.name}")
        return
    
    from backends.tenancy.utils.role_manager import StudyRoleManager
    
    try:
        result = StudyRoleManager.assign_permissions(study_code, force=True)
        
        if result.get('permissions_assigned', 0) > 0 or result.get('permissions_removed', 0) > 0:
            logger.info(
                f"Auto-synced permissions for study {study_code}: "
                f"Assigned {result.get('permissions_assigned', 0)}, "
                f"removed {result.get('permissions_removed', 0)} permissions"
            )
            
    except Exception as e:
        logger.error(
            f"Failed to sync permissions for study {study_code}: {e}",
            exc_info=True
        )

# ==========================================
# MEMBERSHIP SYNC SIGNALS
# ==========================================

@receiver(post_save, sender='tenancy.StudyMembership')
def sync_groups_on_membership_change(sender, instance, created, **kwargs):
    """Sync user groups when membership changes"""
    try:
        from backends.tenancy.utils import TenancyUtils
        
        if instance.user:
            result = TenancyUtils.sync_user_groups(instance.user)
            
            if created:
                logger.info(
                    f"Created membership for {instance.user.username} "
                    f"in study {instance.study.code}"
                )
            
            if result['added'] > 0 or result['removed'] > 0:
                logger.debug(
                    f"Synced groups for {instance.user.username}: "
                    f"+{result['added']}, -{result['removed']}"
                )
                
    except Exception as e:
        logger.error(f"Error syncing groups on membership change: {e}")


@receiver(pre_delete, sender='tenancy.StudyMembership')
def sync_groups_on_membership_delete(sender, instance, **kwargs):
    """Sync user groups when membership is deleted"""
    try:
        from backends.tenancy.utils import TenancyUtils
        
        if instance.user:
            # Clear cache before deletion
            TenancyUtils.clear_user_cache(instance.user)
            
            logger.info(
                f"Removing membership for {instance.user.username} "
                f"from study {instance.study.code}"
            )
            
    except Exception as e:
        logger.error(f"Error handling membership deletion: {e}")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _is_study_app(app_config: AppConfig) -> bool:
    """Check if app is a study app"""
    if not hasattr(app_config, 'name'):
        return False
    
    return app_config.name.startswith('backends.studies.study_')


def _extract_study_code_from_app(app_config: AppConfig) -> Optional[str]:
    """Extract study code from app name"""
    if not hasattr(app_config, 'name'):
        return None
    
    app_name = app_config.name
    
    parts = app_name.split('.')
    if len(parts) < 3:
        return None
    
    study_app_name = parts[-1]
    
    if not study_app_name.startswith('study_'):
        return None
    
    study_code = study_app_name.replace('study_', '', 1).upper()
    
    return study_code if study_code else None

# ==========================================
# PERIODIC CLEANUP TASKS
# ==========================================

def cleanup_expired_sessions():
    """
    Clean up expired sessions and their related data
    Should be called periodically (e.g., via Celery)
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        # Delete expired sessions
        expired_count = Session.objects.filter(
            expire_date__lt=timezone.now()
        ).delete()[0]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions")
        
        # Clean up idle connections
        DatabaseConnectionManager.cleanup_idle_connections()
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")


def cleanup_old_access_logs():
    """
    Clean up old axes access logs
    Should be called periodically to prevent table bloat
    """
    try:
        from axes.models import AccessLog
        from django.utils import timezone
        from datetime import timedelta
        
        # Keep logs for 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count = AccessLog.objects.filter(
            attempt_time__lt=cutoff_date
        ).delete()[0]
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old access logs")
            
    except Exception as e:
        logger.error(f"Error cleaning access logs: {e}")