# backend/tenancy/signals.py - UPDATED VERSION
"""
Optimized signal handlers for tenancy system

UPDATED: Enhanced auto_create_study_database signal with clearer messages
"""
from django.core.signals import request_finished, request_started
from django.db import connections, models
from django.conf import settings
from django.core.cache import cache
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_login_failed
from axes.signals import user_locked_out
from django.utils import timezone
from django.db.models import F, Value
from django.db.models.functions import Concat
import logging

from typing import Any, Optional
from django.db.models.signals import post_save, post_migrate, pre_delete
from django.apps import AppConfig

logger = logging.getLogger(__name__)


# ==========================================
# AXES SIGNAL HANDLERS
# ==========================================

@receiver(user_locked_out)
def handle_axes_lockout(sender, request, username, ip_address, **kwargs):
    """Handle Axes lockout event"""
    from backends.tenancy.models.user import User
    
    try:
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        note_text = f"\n[{now}] Auto-blocked by axes from IP {ip_address}"
        
        updated = User.objects.filter(
            username=username,
            is_active=True
        ).update(
            is_active=False,
            notes=Concat(
                F('notes'),
                Value(note_text),
                output_field=models.TextField()
            )
        )
        
        if updated:
            logger.warning(
                f"SECURITY: User '{username}' deactivated due to axes lockout from IP {ip_address}"
            )
            
            cache_keys = [
                f'user_{username}',
                f'user_blocked_{username}',
                f'user_obj_{username}',
            ]
            cache.delete_many(cache_keys)
            
    except Exception as e:
        logger.error(f"Error handling axes lockout for '{username}': {e}", exc_info=True)


@receiver(user_logged_in)
def handle_successful_login(sender, request, user, **kwargs):
    """Handle successful login"""
    from backends.tenancy.models.user import User
    
    try:
        if not user.is_active:
            logger.error(f"WARNING: Inactive user '{user.username}' logged in - shouldn't happen!")
            return
        
        User.objects.filter(pk=user.pk).update(
            failed_login_attempts=0,
            last_failed_login=None,
            last_login=timezone.now()
        )
        
        cache.set(
            f'user_login_{user.pk}',
            {
                'username': user.username,
                'last_login': timezone.now().isoformat(),
            },
            timeout=300
        )
        
        logger.debug(f"User '{user.username}' logged in successfully")
        
    except Exception as e:
        logger.error(f"Error handling successful login for '{user.username}': {e}", exc_info=True)


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    """Handle failed login attempts"""
    from backends.tenancy.models.user import User
    
    username = credentials.get('username')
    if not username:
        return
    
    try:
        User.objects.filter(username=username).update(
            failed_login_attempts=F('failed_login_attempts') + 1,
            last_failed_login=timezone.now()
        )
        
        logger.debug(f"Failed login attempt for user '{username}'")
        
        from axes.conf import settings as axes_settings
        
        user = User.objects.only(
            'pk', 'username', 'is_active', 'failed_login_attempts'
        ).filter(username=username).first()
        
        if user and user.failed_login_attempts >= axes_settings.AXES_FAILURE_LIMIT:
            if user.is_active:
                now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                note_text = f"\n[{now}] Auto-blocked: Too many failed attempts"
                
                User.objects.filter(pk=user.pk).update(
                    is_active=False,
                    notes=Concat(F('notes'), Value(note_text), output_field=models.TextField())
                )
                
                logger.warning(
                    f"User '{username}' auto-blocked after {user.failed_login_attempts} attempts"
                )
                
                cache.delete_many([
                    f'user_{username}',
                    f'user_blocked_{username}',
                    f'user_obj_{user.pk}',
                ])
                
    except Exception as e:
        logger.error(f"Error handling failed login for '{username}': {e}", exc_info=True)


# ==========================================
# REQUEST LIFECYCLE HANDLERS
# ==========================================

@receiver(request_started)
def handle_request_start(sender, environ, **kwargs):
    """Handle request start"""
    try:
        from backends.tenancy.db_router import clear_current_db
        clear_current_db()
        
        if settings.DEBUG:
            path = environ.get('PATH_INFO', '')
            method = environ.get('REQUEST_METHOD', '')
            logger.debug(f"Request started: {method} {path}")
            
    except Exception as e:
        logger.error(f"Error in request start handler: {e}")


@receiver(request_finished)
def handle_request_finished(sender, **kwargs):
    """Cleanup after request"""
    try:
        cleaned = 0
        
        study_aliases = [
            alias for alias in list(connections.databases.keys())
            if alias != 'default' and alias.startswith(settings.STUDY_DB_PREFIX)
        ]
        
        for alias in study_aliases:
            try:
                conn_wrapper = connections[alias]
                
                if hasattr(conn_wrapper, 'connection') and conn_wrapper.connection is not None:
                    should_close = False
                    
                    if hasattr(conn_wrapper, 'queries') and len(conn_wrapper.queries) > 100:
                        should_close = True
                        logger.debug(f"Closing {alias}: too many queries ({len(conn_wrapper.queries)})")
                    
                    elif not conn_wrapper.is_usable():
                        should_close = True
                        logger.debug(f"Closing {alias}: connection unusable")
                    
                    if should_close:
                        conn_wrapper.close()
                        cleaned += 1
                        
            except Exception as e:
                logger.error(f"Error checking connection {alias}: {e}")
        
        from backends.tenancy.db_router import clear_current_db
        clear_current_db()
        
        if cleaned > 0 and settings.DEBUG:
            logger.debug(f"Cleaned up {cleaned} database connection(s)")
            
    except Exception as e:
        logger.error(f"Error in request finished handler: {e}")


# ==========================================
# STUDY ACCESS TRACKING
# ==========================================

def track_study_access_signal(user, study):
    """Track when user accesses a study"""
    from backends.tenancy.models.user import User
    
    try:
        cache_key = f'study_access_{user.pk}_{study.pk}'
        last_tracked = cache.get(cache_key)
        
        now = timezone.now()
        
        if not last_tracked or (now - last_tracked).seconds > 300:
            User.objects.filter(pk=user.pk).update(
                last_study_accessed=study,
                last_study_accessed_at=now
            )
            
            cache.set(cache_key, now, timeout=300)
            logger.debug(f"Updated study access: user {user.pk} -> study {study.code}")
            
    except Exception as e:
        logger.error(f"Error tracking study access: {e}")


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
        specific_keys = [
            f'user_{user.pk}',
            f'user_obj_{user.pk}',
            f'user_blocked_{user.username}',
            f'user_login_{user.pk}',
            f'user_studies_{user.pk}',
        ]
        
        cache.delete_many(specific_keys)
        cleared = len(specific_keys)
        
        if hasattr(cache, 'delete_pattern'):
            patterns = [
                f'perms_{user.pk}_*',
                f'sites_{user.pk}_*',
                f'study_access_{user.pk}_*',
                f'mw_study_*_{user.pk}',
            ]
            
            for pattern in patterns:
                try:
                    cleared += cache.delete_pattern(pattern)
                except Exception as e:
                    logger.debug(f"Could not delete pattern {pattern}: {e}")
        
        logger.debug(f"Cleared {cleared} cache key(s) for user {user.pk}")
        return cleared
        
    except Exception as e:
        logger.error(f"Error clearing user cache: {e}")
        return 0


def clear_study_cache(study):
    """Clear all cached data for a study"""
    try:
        specific_keys = [
            f'study_stats_{study.pk}',
            f'db_config_{study.db_name}',
        ]
        
        cache.delete_many(specific_keys)
        cleared = len(specific_keys)
        
        if hasattr(cache, 'delete_pattern'):
            patterns = [
                f'*_{study.pk}',
                f'study_{study.pk}_*',
                f'mw_study_{study.pk}_*',
            ]
            
            for pattern in patterns:
                try:
                    cleared += cache.delete_pattern(pattern)
                except Exception as e:
                    logger.debug(f"Could not delete pattern {pattern}: {e}")
        
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
    UPDATED: Clearer messages and better instructions
    
    Automatically create database when Study is created/activated
    
    Steps:
    1. Create PostgreSQL database
    2. Create 'data' schema  
    3. Register in Django (manual restart required)
    4. Initialize roles
    
    User must restart Django server to load the new app
    """
    # Determine if we should create database
    should_create = False
    action = None
    
    if created:
        # New study created
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
    
    # UPDATED: Better logging format
    logger.debug("=" * 70)
    logger.debug(f"AUTO-CREATING DATABASE FOR STUDY {instance.code}")
    logger.debug("=" * 70)
    logger.debug(f"Action: {action}")
    logger.debug(f"Database: {db_name}")
    logger.debug(f"Schema: {settings.STUDY_DB_SCHEMA}")
    
    try:
        from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
        
        # Check if database already exists
        exists = DatabaseStudyCreator.database_exists(db_name)
        
        if exists:
            logger.debug(f"Database '{db_name}' already exists")
            
            # Ensure schema exists
            from backends.tenancy.db_loader import study_db_manager
            schema_ok = study_db_manager.ensure_schema_exists(db_name)
            
            if schema_ok:
                logger.debug(f"Schema '{settings.STUDY_DB_SCHEMA}' verified")
            
            # Register in Django
            _register_database_dynamically(instance)
            
        else:
            # UPDATED: Clearer creation message
            logger.debug(f"Creating new database '{db_name}'...")
            
            # Create database
            success, message = DatabaseStudyCreator.create_study_database(db_name)
            
            if success:
                logger.debug(f"{message}")
                
                # Ensure schema
                from backends.tenancy.db_loader import study_db_manager
                study_db_manager.ensure_schema_exists(db_name)
                
                # Register in Django
                _register_database_dynamically(instance)
                
                # UPDATED: Better formatted next steps
                logger.debug("")
                logger.debug("=" * 70)
                logger.debug(f"STUDY {instance.code} DATABASE CREATED")
                logger.debug("=" * 70)
                logger.debug(f"Database: {db_name}")
                logger.debug(f"Schema: {settings.STUDY_DB_SCHEMA}")
                logger.debug("")
                logger.debug("Next Steps:")
                logger.debug("")
                logger.debug(f"  1. Create folder structure:")
                logger.debug(f"     python manage.py create_study_structure {instance.code}")
                logger.debug("")
                logger.debug(f"  2. Restart Django server:")
                logger.debug(f"     Ctrl+C, then: python manage.py runserver")
                logger.debug("")
                logger.debug(f"  3. Run migrations:")
                logger.debug(f"     python manage.py migrate --database {db_name}")
                logger.debug("")
                logger.debug(f"  4. (Optional) Create API:")
                logger.debug(f"     python manage.py create_study_api {instance.code}")
                logger.debug("")
                logger.debug("=" * 70)
                
            else:
                # UPDATED: Clearer error message
                logger.error("=" * 70)
                logger.error(f"FAILED TO CREATE DATABASE")
                logger.error("=" * 70)
                logger.error(f"Error: {message}")
                logger.error("")
                logger.error("Try creating manually:")
                logger.error(f"   python manage.py create_study_db {instance.code}")
                logger.error("=" * 70)
                return
        
        # Auto-initialize roles
        _auto_initialize_roles(instance)
        
    except Exception as e:
        # UPDATED: Better error logging
        logger.error("=" * 70)
        logger.error(f"ERROR IN AUTO-CREATE DATABASE")
        logger.error("=" * 70)
        logger.error(f"Study: {instance.code}")
        logger.error(f"Database: {db_name}")
        logger.error(f"Error: {e}")
        logger.error("=" * 70)
        logger.error(f"", exc_info=True)


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
        db_config = DatabaseConfig.get_study_db_config(db_name)
        
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


@receiver(pre_delete, sender='tenancy.Study')
def warn_before_study_deletion(sender, instance, **kwargs):
    """
    Warn before deleting a study
    UPDATED: Better formatted warning
    """
    logger.warning("")
    logger.warning("=" * 70)
    logger.warning(f"STUDY {instance.code} IS BEING DELETED")
    logger.warning("=" * 70)
    logger.warning(f"Database: {instance.db_name}")
    logger.warning("")
    logger.warning("NOTE: The PostgreSQL database is NOT automatically deleted.")
    logger.warning("")
    logger.warning("To manually delete the database:")
    logger.warning("")
    logger.warning("  1. Via management command:")
    logger.warning(f"     python manage.py shell")
    logger.warning(f"     >>> from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator")
    logger.warning(f"     >>> DatabaseStudyCreator.drop_study_database('{instance.db_name}', force=True)")
    logger.warning("")
    logger.warning("  2. Via SQL:")
    logger.warning(f"     DROP DATABASE {instance.db_name};")
    logger.warning("")
    logger.warning("=" * 70)


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
        
        logger.debug(
            f"Auto-initialized study {study_code}: "
            f"Created {result['groups_created']} groups, "
            f"assigned {result['permissions_assigned']} permissions "
            f"across {result['models_found']} models"
        )
        
    except Exception as e:
        logger.error(
            f"Failed to auto-create roles for study {study_code}: {e}",
            exc_info=True,
            extra={'study_code': study_code}
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
        logger.warning(
            f"Could not extract study code from app: {sender.name}",
            extra={'app_name': sender.name}
        )
        return
    
    from backends.tenancy.utils.role_manager import StudyRoleManager
    
    try:
        result = StudyRoleManager.assign_permissions(study_code, force=True)
        
        if result['permissions_assigned'] > 0 or result['permissions_removed'] > 0:
            logger.debug(
                f"Auto-synced permissions for study {study_code}: "
                f"Assigned {result['permissions_assigned']}, "
                f"removed {result['permissions_removed']}, "
                f"updated {result['groups_updated']} groups "
                f"({result['models_found']} models detected)"
            )
        else:
            logger.debug(
                f"No permission changes for study {study_code} "
                f"({result['models_found']} models checked)"
            )
            
    except Exception as e:
        logger.error(
            f"Failed to sync permissions for study {study_code}: {e}",
            exc_info=True,
            extra={'study_code': study_code, 'app_name': sender.name}
        )


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