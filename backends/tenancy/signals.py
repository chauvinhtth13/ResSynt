# backend/tenancy/signals.py - Complete rewrite for allauth + axes

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.db import connections
from django.db.models.signals import post_migrate, post_save
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
    Handle successful login via allauth.
    Reset axes attempts for THIS USER only (even if < 7 failures).
    """
    try:
        # Regenerate session to prevent fixation attack
        if hasattr(request, 'session'):
            request.session.cycle_key()
        
        # Reset axes attempts for this user only
        from axes.utils import reset
        from axes.models import AccessAttempt
        
        # Check current failures before reset (for logging)
        current_failures = AccessAttempt.objects.filter(
            username__iexact=user.username
        ).values_list('failures_since_start', flat=True).first() or 0
        
        # Reset all attempts for this username
        reset(username=user.username)
        
        if current_failures > 0:
            logger.info(
                f"User {user.username} logged in successfully. "
                f"Reset {current_failures} failed attempt(s)."
            )
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        logger.info(f"User {user.username} logged in from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Error in handle_allauth_login: {e}")


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
    Log blocked user login attempts.
    Axes handles failure tracking automatically via signal.
    """
    username = credentials.get('login') or credentials.get('username') if isinstance(credentials, dict) else str(credentials or '')
    
    if not username or username == 'unknown':
        return
        
    try:
        from backends.tenancy.models import User
        user = User.objects.filter(username__iexact=username).first()
        if user and not user.is_active:
            ip = request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'
            logger.warning(f"Blocked user '{username}' login attempt from {ip}")
    except Exception:
        pass


# ==========================================
# AXES LOCKOUT SIGNAL
# ==========================================

@receiver(user_locked_out)
def handle_axes_lockout(request, credentials, **kwargs):
    """
    Handle axes lockout event
    FIXED: Updated signature for axes 8.0.0 compatibility
    ENHANCED: Using Celery for async email alerts
    
    Axes 8.0.0 sends: request, credentials (dict with 'username'), **kwargs
    """
    try:
        # Extract username from credentials (axes 8.0.0 format)
        username = credentials.get('username', 'unknown') if isinstance(credentials, dict) else str(credentials)
        ip_address = request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.warning(
            f"AXES LOCKOUT: User '{username}' locked out from IP {ip_address}"
        )
        
        # Update user record to track lockout
        from backends.tenancy.models import User
        from backends.tenancy.tasks import send_security_alert
        
        try:
            user = User.objects.get(username=username)
            user.notes = (
                f"{user.notes}\n[{timestamp}] Lockout from {ip_address}"
            ).strip()
            user.save(update_fields=['notes'])
            
            # Send async email alert via Celery
            send_security_alert.delay(
                alert_type='user_lockout',
                details={
                    'username': username,
                    'ip_address': ip_address,
                    'timestamp': timestamp,
                }
            )
            logger.info(f"Queued alert email for lockout: {username}")
                
        except User.DoesNotExist:
            # Log attempt for non-existent user
            logger.info(f"Lockout attempt for non-existent user: {username}")
            
            # Send async alert for non-existent user (potential attack)
            send_security_alert.delay(
                alert_type='invalid_user_attempt',
                details={
                    'username': username,
                    'ip_address': ip_address,
                    'timestamp': timestamp,
                }
            )
            logger.info(f"Queued alert email for non-existent user: {username}")
            
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
# Note: clear_user_cache and clear_study_cache are in TenancyUtils
# Use: from backends.tenancy.utils import TenancyUtils
# TenancyUtils.clear_user_cache(user) / TenancyUtils.clear_study_cache(study)


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
        from config.settings import DatabaseConfig, env
        
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

# Note: auto_create_study_roles functionality is handled by _auto_initialize_roles
# called from auto_create_study_database signal - no need for duplicate signal


@receiver(post_migrate)
def sync_study_permissions_after_migrate(sender: AppConfig, **kwargs: Any) -> None:
    """
    Automatically sync groups and permissions after migrations for study apps.
    
    This signal ensures:
    1. Groups are created for the study (if they don't exist)
    2. Permissions are assigned to groups based on role templates
    
    Note: This signal runs after each app's migrations. Permissions may not exist
    yet if django.contrib.auth's post_migrate hasn't run. This is handled gracefully
    by StudyRoleManager.assign_permissions() which returns early if no permissions found.
    
    For reliable permission sync, use the management command:
        python manage.py sync_study_permissions
    """
    if not _is_study_app(sender):
        return
    
    study_code = _extract_study_code_from_app(sender)
    if not study_code:
        logger.warning(f"Could not extract study code from app: {sender.name}")
        return
    
    from backends.tenancy.utils.role_manager import StudyRoleManager
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    
    try:
        # Check if permissions exist for this app before attempting sync
        app_label = f'study_{study_code.lower()}'
        content_types_exist = ContentType.objects.filter(app_label=app_label).exists()
        permissions_exist = Permission.objects.filter(content_type__app_label=app_label).exists()
        
        if not content_types_exist:
            # ContentTypes not created yet - this is expected during initial migration
            logger.debug(
                f"ContentTypes for {app_label} not ready yet. "
                f"Permissions will be synced after migrations complete."
            )
            return
        
        if not permissions_exist:
            # ContentTypes exist but Permissions don't - auth's post_migrate hasn't run yet
            logger.debug(
                f"Permissions for {app_label} not created yet. "
                f"This is normal - auth app creates permissions after all migrations."
            )
            return
        
        # Permissions exist, proceed with sync
        result = StudyRoleManager.assign_permissions(study_code, force=True)
        
        total_changes = result.get('permissions_assigned', 0) + result.get('permissions_removed', 0)
        
        if total_changes > 0:
            logger.info(
                f"Auto-synced permissions for study {study_code}: "
                f"Assigned {result.get('permissions_assigned', 0)}, "
                f"removed {result.get('permissions_removed', 0)} permissions"
            )
        else:
            logger.debug(f"Permissions already in sync for study {study_code}")
            
    except Exception as e:
        logger.error(
            f"Failed to sync permissions for study {study_code}: {e}",
            exc_info=True
        )

# ==========================================
# NOTE: Membership sync signals are in models/permission.py
# sync_groups_on_save (post_save) and sync_groups_on_delete (post_delete)
# to keep signals close to model definition
# ==========================================

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

# Note: cleanup_expired_sessions is available as Celery task
# Use: from backends.tenancy.tasks import cleanup_expired_sessions_task
# cleanup_expired_sessions_task.delay()


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