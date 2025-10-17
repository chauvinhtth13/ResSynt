# backend/tenancy/signals.py - COMPLETE PRODUCTION VERSION
"""
Signal handlers for Tenancy app

FEATURES:
- Auto-create study databases when Study is created
- Auto-sync permissions after study migrations
- Track user password changes
- Proper database routing for ContentTypes queries

FIXED:
- Database check in post_migrate (only fires for study databases)
- Pylance type annotation errors
- Unicode characters replaced with ASCII (Windows compatibility)

SIGNALS:
1. post_save(Study) -> Create database
2. post_migrate(study app) -> Sync permissions (only when migrating study DB)
3. post_save(User) -> Track password changes
4. post_save(StudyMembership) -> Sync user to groups
"""
import logging
from typing import Any, TYPE_CHECKING
from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.utils import timezone

# Type checking imports (won't be evaluated at runtime)
if TYPE_CHECKING:
    from backends.tenancy.models.user import User as UserType
    from backends.tenancy.models.study import Study as StudyType
    from backends.tenancy.models.permission import StudyMembership as MembershipType

from backends.tenancy.models.study import Study

logger = logging.getLogger(__name__)
User = get_user_model()


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
    return (
        app_config.name.startswith('backends.studies.study_') or
        app_config.label.startswith('study_')
    )


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
        if '.' in app_config.name:
            parts = app_config.name.split('.')
            if len(parts) >= 3 and parts[-1].startswith('study_'):
                code = parts[-1].replace('study_', '')
                return code.upper()
        
        # Try from app label (short name)
        if app_config.label.startswith('study_'):
            code = app_config.label.replace('study_', '')
            return code.upper()
            
    except Exception as e:
        logger.error(
            f"Error extracting study code from app {app_config.name}: {e}",
            exc_info=True
        )
    
    return ""


# ==========================================
# STUDY - DATABASE CREATION
# ==========================================

@receiver(post_save, sender=Study)
def auto_create_study_database(
    sender: "type[StudyType]",
    instance: Study,
    created: bool,
    **kwargs: Any
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
def sync_study_permissions_after_migrate(
    sender: AppConfig,
    **kwargs: Any
) -> None:
    """
    Auto-sync permissions after migrations for study apps
    
    CRITICAL FIX: 
    - Only fires when migrating STUDY database
    - Checks if contenttypes table exists before querying
    """
    # Get which database is being migrated
    using = kwargs.get('using', 'default')
    
    # Get study database prefix from settings
    study_db_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
    
    # Only process if migrating a study database
    if not using.startswith(study_db_prefix):
        logger.debug(
            f"post_migrate on database '{using}' - skipping study permission sync "
            f"(only processes study databases)"
        )
        return
    
    # Only process study apps
    if not _is_study_app(sender):
        logger.debug(
            f"post_migrate for non-study app '{sender.name}' - skipping"
        )
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
    
    db_name = using
    app_label = f'study_{study_code.lower()}'
    
    # Start logging
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"POST-MIGRATE SIGNAL: Study {study_code}")
    logger.info("=" * 70)
    logger.info(f"App name: {sender.name}")
    logger.info(f"App label: {app_label}")
    logger.info(f"Database: {db_name}")
    
    from backends.tenancy.utils.role_manager import StudyRoleManager
    from django.contrib.contenttypes.models import ContentType
    from django.db import connections
    
    try:
        # Verify database is configured
        if db_name not in connections.databases:
            logger.error(
                f"[ERROR] Database '{db_name}' not configured in Django settings. "
                f"Restart the server to load the database configuration."
            )
            logger.info("=" * 70)
            return
        
        # ✅ CRITICAL FIX: Check if contenttypes table exists
        logger.info(f"Checking if contenttypes is migrated to database: {db_name}")
        
        with connections[db_name].cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name = 'django_content_type'
                )
            """)
            
            table_exists = cursor.fetchone()[0] # type: ignore
        
        if not table_exists:
            logger.warning(
                f"Table 'django_content_type' does not exist in database '{db_name}'. "
                f"Contenttypes app has not been migrated to this database yet. "
                f"Run: python manage.py migrate contenttypes --database {db_name}"
            )
            logger.warning(
                f"Permissions will be synced after contenttypes is migrated."
            )
            logger.info("=" * 70)
            return
        
        logger.info(f"[OK] Contenttypes table exists in database: {db_name}")
        
        # Query ContentTypes from STUDY database
        logger.info(f"Checking ContentTypes for app '{app_label}'...")
        
        ct_count = ContentType.objects.using(db_name).filter(
            app_label=app_label
        ).count()
        
        logger.info(f"ContentTypes found: {ct_count}")
        
        if ct_count == 0:
            logger.warning(
                f"No ContentTypes found for app '{app_label}' in database '{db_name}'. "
                f"This means migrations haven't created any models yet, or models have no permissions. "
                f"Permissions will be synced after models are migrated."
            )
            logger.info("=" * 70)
            return
        
        # List models for debugging
        content_types = ContentType.objects.using(db_name).filter(
            app_label=app_label
        ).values_list('model', flat=True)
        
        logger.info(f"Models found: {', '.join(content_types)}")
        
        # Step 1: Initialize study (create/verify groups)
        logger.info("")
        logger.info("Step 1: Creating/verifying Django Groups...")
        
        init_result = StudyRoleManager.initialize_study(study_code, force=False)
        
        if 'error' in init_result:
            logger.error(f"[ERROR] Failed to initialize study: {init_result['error']}")
            logger.info("=" * 70)
            return
        
        groups_created = init_result.get('groups_created', 0)
        groups_existing = init_result.get('groups_existing', 0)
        
        logger.info(
            f"[OK] Groups ready: {groups_created} created, {groups_existing} already existed"
        )
        
        # Step 2: Assign permissions to groups
        logger.info("")
        logger.info("Step 2: Syncing permissions to groups...")
        
        perm_result = StudyRoleManager.assign_permissions(study_code, force=True)
        
        perms_assigned = perm_result.get('permissions_assigned', 0)
        perms_removed = perm_result.get('permissions_removed', 0)
        groups_updated = perm_result.get('groups_updated', 0)
        
        logger.info(
            f"[OK] Permissions synced: "
            f"{perms_assigned} assigned, "
            f"{perms_removed} removed, "
            f"{groups_updated} groups updated"
        )
        
        # Success summary
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"[SUCCESS] Study {study_code} permissions synced")
        logger.info("=" * 70)
        logger.info("")
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error(f"[ERROR] Failed to sync permissions for study {study_code}")
        logger.error("=" * 70)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 70)
        logger.error("")
        
        # Detailed traceback for debugging
        import traceback
        logger.debug("Detailed traceback:")

# ==========================================
# USER - PASSWORD CHANGE TRACKING
# ==========================================

@receiver(post_save, sender=User)
def track_password_changes(
    sender: "type[UserType]",
    instance: Any,
    created: bool,
    **kwargs: Any
) -> None:
    """
    Track when user's password is changed
    
    Updates password_changed_at field when password is modified.
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
    update_fields = kwargs.get('update_fields')
    
    if update_fields and 'password' in update_fields:
        # Password was changed via update(password=...)
        # Update password_changed_at
        User.objects.filter(pk=instance.pk).update(
            password_changed_at=timezone.now()
        )
        
        logger.debug(
            f"Password changed for user '{instance.username}' - "
            f"updated password_changed_at"
        )


# ==========================================
# STUDY MEMBERSHIP - GROUP SYNC
# ==========================================

@receiver(post_save, sender='tenancy.StudyMembership')
def sync_user_to_group_on_membership_change(
    sender: "type[MembershipType]",
    instance: Any,
    created: bool,
    **kwargs: Any
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
    # Only sync if membership is active and has a group
    if not instance.is_active or not instance.group:
        return
    
    try:
        # Sync this specific membership
        instance.sync_user_to_group()
        
        logger.debug(
            f"Synced user '{instance.user.username}' to group '{instance.group.name}' "
            f"for study {instance.study.code}"
        )
        
    except Exception as e:
        logger.error(
            f"Failed to sync user '{instance.user.username}' to group: {e}",
            exc_info=True
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