# backend/tenancy/signals.py - FIXED VERSION (CHỈ SỬA LỖI)
import logging
from typing import Any, TYPE_CHECKING

from django.apps import AppConfig
from django.conf import settings
from django.core.cache import cache
from django.core.signals import request_finished, request_started
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db import connections, models, transaction
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.utils import timezone

from axes.signals import user_locked_out

from backends.tenancy.models.study import Study

if TYPE_CHECKING:
    from backends.tenancy.models.user import User as UserType
    from backends.tenancy.models.study import Study as StudyType
    from backends.tenancy.models.permission import StudyMembership as MembershipType

logger = logging.getLogger(__name__)
User = get_user_model()

# ==========================================
# AUTHENTICATION SIGNAL HANDLERS
# ==========================================

@receiver(user_logged_in)
def handle_successful_login(sender, request, user, **kwargs):
    """
    Handle successful login - Reset counters and cache user info.
    
    OPTIMIZED: Single update query, efficient caching
    """
    if not user:
        return
    
    try:
        now = timezone.now()
        
        # Single atomic update
        with transaction.atomic():
            User.objects.filter(pk=user.pk).update(
                failed_login_attempts=0,
                last_failed_login=None,
                last_login=now
            )
        
        # Cache user login info
        cache_key = f"user_login_{user.pk}"
        cache_data = {
            "username": user.username,
            "last_login": now.isoformat(),
            "is_superuser": user.is_superuser,
        }
        cache.set(cache_key, cache_data, timeout=300)  # 5 minutes
        
        logger.info(f"User '{user.username}' logged in successfully from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Error handling successful login for user {user.pk}: {e}", exc_info=True)


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    """
    Track failed login attempts for audit purposes.
    
    SIMPLIFIED: Chỉ track, không block. Axes sẽ handle blocking.
    """
    username = credentials.get("username")
    if not username:
        return
    
    try:
        # Update failed login counter for tracking/audit
        with transaction.atomic():
            updated = User.objects.filter(username=username).update(
                failed_login_attempts=F("failed_login_attempts") + 1,
                last_failed_login=timezone.now()
            )
        
        if updated:
            logger.warning(
                f"Failed login attempt for '{username}' from {request.META.get('REMOTE_ADDR', 'unknown')}"
            )
        
    except Exception as e:
        logger.error(f"Error tracking failed login for '{username}': {e}")


# ==========================================
# REQUEST LIFECYCLE HANDLERS
# ==========================================

import threading
_request_local = threading.local()


@receiver(request_started)
def handle_request_start(sender, environ, **kwargs):
    """Initialize request context and clear stale database connections."""
    try:
        # Clear database routing context
        from backends.tenancy.db_router import clear_current_db
        clear_current_db()
        
        # Initialize request tracking
        _request_local.study_dbs_used = set()
        _request_local.request_start = timezone.now()
        
        if settings.DEBUG:
            path = environ.get('PATH_INFO', 'unknown')
            method = environ.get('REQUEST_METHOD', 'unknown')
            logger.debug(f"Request started: {method} {path}")
            
    except Exception as e:
        logger.error(f"Error in request_started handler: {e}")


@receiver(request_finished)
def handle_request_finished(sender, **kwargs):
    """Clean up request context and log performance metrics."""
    try:
        # Clear database context
        from backends.tenancy.db_router import clear_current_db
        clear_current_db()
        
        # Log performance metrics in DEBUG mode
        if settings.DEBUG and hasattr(_request_local, 'request_start'):
            duration = (timezone.now() - _request_local.request_start).total_seconds()
            
            if duration > 1.0:  # Log slow requests
                logger.warning(f"Slow request detected: {duration:.2f}s")
        
        # Clean up request-local storage
        if hasattr(_request_local, 'study_dbs_used'):
            del _request_local.study_dbs_used
        if hasattr(_request_local, 'request_start'):
            del _request_local.request_start
            
    except Exception as e:
        logger.error(f"Error in request_finished handler: {e}")


# ==========================================
# STUDY ACCESS TRACKING
# ==========================================


def track_study_access_signal(user, study):
    """Track when user accesses a study"""
    from backends.tenancy.models.user import User

    try:
        cache_key = f"study_access_{user.pk}_{study.pk}"
        last_tracked = cache.get(cache_key)

        now = timezone.now()

        # FIX: Debounce - chá»‰ update DB má»—i 5 phÃºt
        if not last_tracked or (now - last_tracked).seconds > 300:
            User.objects.filter(pk=user.pk).update(
                last_study_accessed=study, last_study_accessed_at=now
            )

            cache.set(cache_key, now, timeout=300)
            logger.debug(f"Updated study access: user {user.pk} -> study {study.code}")

    except Exception as e:
        logger.error(f"Error tracking study access: {e}")


# ==========================================
# HELPER FUNCTIONS
# ==========================================


def _is_study_app(app_config: AppConfig) -> bool:
    """
    Check if app config represents a study app

    Args:
        app_config: Django app configuration

    Returns:
        True if this is a study app
    """
    return app_config.name.startswith(
        "backends.studies.study_"
    ) or app_config.label.startswith("study_")


def _extract_study_code_from_app(app_config: AppConfig) -> str:
    """
    Extract study code from app config

    Args:
        app_config: Django app configuration

    Returns:
        Study code (uppercase) or empty string if extraction fails

    Example:
        'backends.studies.study_43en' -> '43EN'
        'study_44en' -> '44EN'
    """
    try:
        # Try from app name first (full path)
        if "." in app_config.name:
            parts = app_config.name.split(".")
            if len(parts) >= 3 and parts[-1].startswith("study_"):
                code = parts[-1].replace("study_", "")
                return code.upper()

        # Try from app label (short name)
        if app_config.label.startswith("study_"):
            code = app_config.label.replace("study_", "")
            return code.upper()

    except Exception as e:
        logger.error(
            f"Error extracting study code from app {app_config.name}: {e}",
            exc_info=True,
        )

    return ""


# ==========================================
# STUDY - DATABASE CREATION
# ==========================================


@receiver(post_save, sender=Study)
def auto_create_study_database(
    sender: "type[StudyType]", instance: Study, created: bool, **kwargs: Any
) -> None:
    """
    Automatically create database when a new Study is created

    This fires when:
        - Admin creates a study via Django admin
        - Code creates a study via Study.objects.create()

    Args:
        sender: Study model class
        instance: The Study instance being saved
        created: True if this is a new instance
        **kwargs: Additional signal arguments
    """
    # Only for new studies
    if not created:
        return

    from backends.tenancy.utils import DatabaseStudyCreator

    db_name = instance.db_name

    logger.info("=" * 70)
    logger.info(f"NEW STUDY CREATED: {instance.code}")
    logger.info("=" * 70)
    logger.info(f"Database name: {db_name}")

    # Check if database already exists
    if DatabaseStudyCreator.database_exists(db_name):
        logger.info(f"Database '{db_name}' already exists - no action needed")
        logger.info("=" * 70)
        return

    # Create database
    logger.info(f"Creating PostgreSQL database: {db_name}")

    success, error = DatabaseStudyCreator.create_study_database(db_name)

    if success:
        logger.info(f"[OK] Database '{db_name}' created successfully")
        logger.info(f"[OK] Schema 'data' created and configured")
        logger.info("=" * 70)
    else:
        logger.error(f"[ERROR] Failed to create database '{db_name}'")
        logger.error(f"Error: {error}")
        logger.error("=" * 70)


# ==========================================
# STUDY - ROLE & PERMISSION MANAGEMENT
# ==========================================

@receiver(post_migrate)
def sync_study_permissions_after_migrate(sender: AppConfig, **kwargs: Any) -> None:
    """
    Auto-sync permissions after migrations for study apps
    
    FIX: Query ContentType từ default database, không phải study database
    """
    # Get which database is being migrated
    using = kwargs.get("using", "default")

    # Get study database prefix from settings
    study_db_prefix = getattr(settings, "STUDY_DB_PREFIX", "db_study_")

    # Only process if migrating a study database
    if not using.startswith(study_db_prefix):
        logger.debug(
            f"post_migrate on database '{using}' - skipping study permission sync "
            f"(only processes study databases)"
        )
        return

    # Only process study apps
    if not _is_study_app(sender):
        logger.debug(f"post_migrate for non-study app '{sender.name}' - skipping")
        return

    # Extract study code
    study_code = _extract_study_code_from_app(sender)

    if not study_code:
        logger.warning(
            f"Could not extract study code from app: {sender.name}. "
            f"Permission sync skipped."
        )
        return

    # Verify database name matches study code
    expected_db_name = f"{study_db_prefix}{study_code.lower()}"

    if using != expected_db_name:
        logger.warning(
            f"Database mismatch: migrating '{using}' but app is for '{expected_db_name}'. "
            f"Skipping permission sync."
        )
        return

    # FIX: Đơn giản hóa logic sync permissions
    try:
        from backends.tenancy.utils.role_manager import StudyRoleManager
        from django.contrib.contenttypes.models import ContentType

        logger.info("=" * 70)
        logger.info(f"SYNCING PERMISSIONS: {study_code}")
        logger.info("=" * 70)
        logger.info(f"Database: {using}")

        # Get study instance from DEFAULT database
        try:
            study = Study.objects.get(code=study_code)
        except Study.DoesNotExist:
            logger.error(
                f"Study '{study_code}' not found in database - cannot sync permissions"
            )
            return

        # ✅ FIX: Query ContentType từ DEFAULT database, không dùng .using(using)
        app_label = f"study_{study_code.lower()}"
        content_type_count = ContentType.objects.filter(  # Bỏ .using(using)
            app_label=app_label
        ).count()

        if content_type_count == 0:
            logger.info(
                f"No content types found for app '{app_label}'. "
                f"Permissions will be synced after models are migrated."
            )
            logger.info("=" * 70)
            return

        # Initialize study groups
        logger.info("Step 1: Creating/verifying Django Groups...")
        init_result = StudyRoleManager.initialize_study(study_code, force=False)

        if "error" in init_result:
            logger.error(f"[ERROR] Failed to initialize study: {init_result['error']}")
            logger.info("=" * 70)
            return

        groups_created = init_result.get("groups_created", 0)
        groups_existing = init_result.get("groups_existing", 0)
        logger.info(
            f"[OK] Groups ready: {groups_created} created, {groups_existing} existing"
        )

        # Assign permissions
        logger.info("Step 2: Syncing permissions to groups...")
        perm_result = StudyRoleManager.assign_permissions(study_code, force=True)

        perms_assigned = perm_result.get("permissions_assigned", 0)
        perms_removed = perm_result.get("permissions_removed", 0)
        groups_updated = perm_result.get("groups_updated", 0)

        logger.info(
            f"[OK] Permissions synced: "
            f"{perms_assigned} assigned, "
            f"{perms_removed} removed, "
            f"{groups_updated} groups updated"
        )

        logger.info("=" * 70)
        logger.info(f"[SUCCESS] Study {study_code} permissions synced")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to sync permissions for study {study_code}: {e}",
            exc_info=True
        )
        logger.error("=" * 70)

# ==========================================
# USER - PASSWORD CHANGE TRACKING
# ==========================================


@receiver(post_save, sender=User)
def track_password_change(
    sender: "type[UserType]", instance: Any, created: bool, **kwargs: Any
) -> None:
    """
    Track when user's password is changed

    This is a fallback - primary tracking is in User.set_password()

    Args:
        sender: User model class
        instance: The User instance being saved
        created: True if this is a new user
        **kwargs: Additional signal arguments
    """
    # Skip for new users (password_changed_at set in creation)
    if created:
        return

    # Check if password was explicitly updated
    update_fields = kwargs.get("update_fields")

    if update_fields and "password" in update_fields:
        # Password was changed via update(password=...)
        # Update password_changed_at
        User.objects.filter(pk=instance.pk).update(password_changed_at=timezone.now())

        logger.debug(
            f"Password changed for user '{instance.username}' - "
            f"updated password_changed_at"
        )


# ==========================================
# STUDY MEMBERSHIP - GROUP SYNC
# ==========================================


@receiver(post_save, sender="tenancy.StudyMembership")
def sync_user_to_group_on_membership_change(
    sender: "type[MembershipType]", instance: Any, created: bool, **kwargs: Any
) -> None:
    """
    Auto-sync user to groups when StudyMembership is created/updated

    Ensures User.groups reflects active StudyMemberships

    Args:
        sender: StudyMembership model class
        instance: The StudyMembership instance
        created: True if new membership
        **kwargs: Additional signal arguments
    """
    # FIX: Add select_related Ä‘á»ƒ trÃ¡nh N+1 queries
    try:
        # Refresh instance with related objects náº¿u chÆ°a cÃ³
        if not hasattr(instance, '_user_cached'):
            from backends.tenancy.models.permission import StudyMembership
            instance = StudyMembership.objects.select_related(
                'user', 'group', 'study'
            ).get(pk=instance.pk)

        # Only sync if membership is active and has a group
        if not instance.is_active or not instance.group:
            return

        # Sync this specific membership
        instance.sync_user_to_group()

        logger.debug(
            f"Synced user '{instance.user.username}' to group '{instance.group.name}' "
            f"for study {instance.study.code}"
        )

    except Exception as e:
        logger.error(
            f"Failed to sync user to group: {e}",
            exc_info=True,
        )


# ==========================================
# INITIALIZATION
# ==========================================


def init_signals() -> None:
    """
    Initialize signals module

    This function is called when Django loads the tenancy app.
    It ensures all signal handlers are registered.
    """
    logger.debug("Tenancy signals initialized")


# Auto-initialize when module is imported
init_signals()