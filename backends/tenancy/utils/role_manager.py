# backend/tenancy/utils/role_manager.py - IMPROVED WITH GRACEFUL ERROR HANDLING
"""
Study Role Management System - Dynamic Model Detection
Automatically manages Django Groups and Permissions for study apps

IMPROVED:
- Graceful handling when tables don't exist yet
- Better error messages and logging
- Safe operations during initial setup
- Clear user guidance

NAMING CONVENTION:
- role_key: Internal identifier (e.g., 'data_manager') - lowercase with underscores
- display_name: Human-readable name (e.g., 'Data Manager') - Title Case with spaces
"""
from typing import Dict, List, Set, Optional, Tuple
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, connection
from django.core.cache import cache
from django.db.utils import OperationalError 
import logging

logger = logging.getLogger(__name__)


# ==========================================
# DATABASE READINESS CHECKER
# ==========================================

class DatabaseReadinessChecker:
    """
    Helper class to check if database tables are ready
    Prevents errors during initial setup
    """
    
    @staticmethod
    def is_table_ready(table_name: str, schema: str = 'public') -> bool:
        """
        Check if a table exists and is accessible
        
        Args:
            table_name: Table name to check
            schema: Schema name (default: 'public')
            
        Returns:
            True if table exists and is accessible
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s
                        AND table_name = %s
                    )
                """, [schema, table_name])
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.debug(f"Cannot check table {schema}.{table_name}: {e}")
            return False
    
    @staticmethod
    def are_auth_tables_ready() -> bool:
        """
        Check if Django auth tables are ready
        Required for Groups and Permissions
        """
        try:
            # Try to query Group model (will fail if tables don't exist)
            Group.objects.count()
            return True
        except OperationalError as e:
            logger.debug(f"Auth tables not ready: {e}")
            return False
        except Exception as e:
            logger.debug(f"Error checking auth tables: {e}")
            return False
    
    @staticmethod
    def are_contenttypes_ready() -> bool:
        """Check if ContentType tables are ready"""
        try:
            ContentType.objects.count()
            return True
        except OperationalError as e:
            logger.debug(f"ContentType tables not ready: {e}")
            return False
        except Exception as e:
            logger.debug(f"Error checking ContentType tables: {e}")
            return False
    
    @staticmethod
    def is_tenancy_ready() -> bool:
        """Check if tenancy tables are ready"""
        try:
            from backends.tenancy.models import Study
            Study.objects.count()
            return True
        except OperationalError as e:
            logger.debug(f"Tenancy tables not ready: {e}")
            return False
        except Exception as e:
            logger.debug(f"Error checking tenancy tables: {e}")
            return False


# ==========================================
# ROLE TEMPLATES
# ==========================================

class RoleTemplate:
    """
    Define role templates that apply to all studies
    Permissions are auto-applied to ALL models in study
    """
    
    # Role definitions with permission patterns
    ROLES = {
        "data_manager": {
            "display_name": "Data Manager",
            "description": "Handles full study access including user management.",
            "permissions": ["add", "change", "delete", "view"],
            "priority": 100,
            "is_privileged": True,
        },
        "research_manager": {
            "display_name": "Research Manager",
            "description": "Manages data entry and oversight.",
            "permissions": ["add", "change", "view"],
            "priority": 80,
            "is_privileged": False,
        },
        "principal_investigator": {
            "display_name": "Principal Investigator",
            "description": "Leads the study with patient management responsibilities.",
            "permissions": ["view"],
            "priority": 70,
            "is_privileged": False,
        },
        "research_monitor": {
            "display_name": "Research Monitor",
            "description": "Conducts study monitoring and data review.",
            "permissions": ["view"],
            "priority": 60,
            "is_privileged": False,
        },
        "research_staff": {
            "display_name": "Research Staff",
            "description": "Performs data entry and patient follow-up.",
            "permissions": ["add", "change", "view"],
            "priority": 50,
            "is_privileged": False,
        },
    }
    
    # Reverse lookup map: display_name -> role_key
    _DISPLAY_NAME_MAP = {info["display_name"]: key for key, info in ROLES.items()}
    
    @classmethod
    def get_all_role_keys(cls) -> List[str]:
        """Get list of all role keys (internal identifiers)"""
        return list(cls.ROLES.keys())
    
    @classmethod
    def get_all_display_names(cls) -> List[str]:
        """Get list of all display names (human-readable)"""
        return [info["display_name"] for info in cls.ROLES.values()]
    
    @classmethod
    def get_role_config(cls, role_key: str) -> Optional[Dict]:
        """Get full configuration for a role"""
        return cls.ROLES.get(role_key)
    
    @classmethod
    def is_valid_role_key(cls, role_key: str) -> bool:
        """Check if role_key is valid"""
        return role_key in cls.ROLES
    
    @classmethod
    def get_display_name(cls, role_key: str) -> str:
        """Convert role_key to display_name"""
        config = cls.get_role_config(role_key)
        return config.get('display_name', role_key) if config else role_key
    
    @classmethod
    def get_role_key(cls, display_name: str) -> Optional[str]:
        """Convert display_name to role_key (reverse lookup)"""
        return cls._DISPLAY_NAME_MAP.get(display_name)
    
    @classmethod
    def get_permissions(cls, role_key: str) -> List[str]:
        """Get permission actions for a role"""
        config = cls.get_role_config(role_key)
        return config.get('permissions', []) if config else []
    
    @classmethod
    def get_description(cls, role_key: str) -> Optional[str]:
        """Get role description"""
        config = cls.get_role_config(role_key)
        return config.get('description') if config else None


# ==========================================
# STUDY ROLE MANAGER (IMPROVED)
# ==========================================

class StudyRoleManager:
    """
    Main manager for study-specific roles and permissions
    
    IMPROVED:
    - Graceful handling when database isn't ready
    - Better error messages and guidance
    - Safe operations during setup
    """
    
    CACHE_TTL = 600  # 10 minutes
    
    @classmethod
    def get_group_name(cls, study_code: str, role_key: str) -> str:
        """Generate study-specific group name"""
        display_name = RoleTemplate.get_display_name(role_key)
        return f"Study {study_code.upper()}.{display_name}"
    
    @classmethod
    def parse_group_name(cls, group_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse group name to extract study_code and role_key"""
        if not group_name.startswith("Study "):
            return None, None
        
        remaining = group_name[6:]
        parts = remaining.split('.', 1)
        
        if len(parts) != 2:
            return None, None
        
        study_code, display_name = parts
        role_key = RoleTemplate.get_role_key(display_name)
        
        if role_key:
            return study_code, role_key
        
        return None, None
    
    @classmethod
    def is_study_group(cls, group_name: str) -> bool:
        """Check if group name is a valid study group"""
        study_code, role_key = cls.parse_group_name(group_name)
        return study_code is not None and role_key is not None
    
    @classmethod
    def _check_prerequisites(cls) -> Tuple[bool, str]:
        """
        Check if prerequisites are met for role operations
        
        Returns:
            (success: bool, error_message: str)
        """
        if not DatabaseReadinessChecker.are_auth_tables_ready():
            return False, (
                "Auth tables not ready. Run: python manage.py migrate"
            )
        
        if not DatabaseReadinessChecker.are_contenttypes_ready():
            return False, (
                "ContentType tables not ready. Run: python manage.py migrate"
            )
        
        return True, ""
    
    @classmethod
    @transaction.atomic
    def create_study_groups(cls, study_code: str, force: bool = False) -> Dict[str, Group]:
        """
        Create all default groups for a study
        
        IMPROVED: Checks prerequisites first
        """
        # Check prerequisites
        ready, error_msg = cls._check_prerequisites()
        if not ready:
            logger.debug(f"Cannot create groups for {study_code}: {error_msg}")
            return {}
        
        try:
            created_groups = {}
            
            for role_key in RoleTemplate.get_all_role_keys():
                group_name = cls.get_group_name(study_code, role_key)
                
                if force:
                    Group.objects.filter(name=group_name).delete()
                
                group, created = Group.objects.get_or_create(name=group_name)
                created_groups[role_key] = group
                
                if created:
                    logger.debug(f"Created group: {group_name}")
            
            return created_groups
            
        except Exception as e:
            logger.error(f"Error creating groups for {study_code}: {e}")
            return {}
    
    @classmethod
    def get_study_models(cls, app_label: str) -> List[str]:
        """
        Get all model names for a study app
        
        IMPROVED: Graceful handling when ContentType not ready
        """
        # Check if ContentType is ready
        if not DatabaseReadinessChecker.are_contenttypes_ready():
            logger.debug(
                f"ContentType not ready for {app_label}. "
                f"Run migrations first."
            )
            return []
        
        try:
            content_types = ContentType.objects.filter(app_label=app_label)
            model_names = [ct.model for ct in content_types]
            
            if model_names:
                logger.debug(f"Found {len(model_names)} models in {app_label}")
            else:
                logger.debug(
                    f"No models found for {app_label}. "
                    f"May need to run: python manage.py migrate --database db_study_{app_label.replace('study_', '')}"
                )
            
            return model_names
            
        except Exception as e:
            logger.debug(f"Error getting models for {app_label}: {e}")
            return []
    
    @classmethod
    def _build_permission_map(cls, app_label: str) -> Dict[str, Dict[str, Permission]]:
        """
        Build a map of permissions organized by model and action
        
        IMPROVED: Safe handling when permissions don't exist
        """
        try:
            all_permissions = Permission.objects.filter(
                content_type__app_label=app_label
            ).select_related('content_type')
            
            permission_map = {}
            for perm in all_permissions:
                model_name = perm.content_type.model
                action = perm.codename.split('_')[0]
                
                if model_name not in permission_map:
                    permission_map[model_name] = {}
                permission_map[model_name][action] = perm
            
            return permission_map
            
        except Exception as e:
            logger.debug(f"Error building permission map for {app_label}: {e}")
            return {}
    
    @classmethod
    @transaction.atomic
    def assign_permissions(cls, study_code: str, force: bool = False) -> Dict[str, int]:
        """
        Assign permissions to study groups based on role templates
        
        IMPROVED: Better error handling and user guidance
        """
        stats = {
            'groups_updated': 0,
            'permissions_assigned': 0,
            'permissions_removed': 0,
            'models_found': 0,
        }
        
        # Check prerequisites
        ready, error_msg = cls._check_prerequisites()
        if not ready:
            logger.debug(f"Cannot assign permissions for {study_code}: {error_msg}")
            return stats
        
        app_label = f'study_{study_code.lower()}'
        
        # Get all models in study app
        model_names = cls.get_study_models(app_label)
        
        if not model_names:
            logger.debug(
                f"No models found for study {study_code}. "
                f"This is normal if migrations haven't been run yet."
            )
            return stats
        
        stats['models_found'] = len(model_names)
        
        try:
            # Get all groups for this study
            groups = {}
            for role_key in RoleTemplate.get_all_role_keys():
                group_name = cls.get_group_name(study_code, role_key)
                try:
                    groups[role_key] = Group.objects.get(name=group_name)
                except Group.DoesNotExist:
                    logger.debug(
                        f"Group not found: {group_name}. "
                        f"Run: python manage.py sync_study_roles --study {study_code}"
                    )
                    continue
            
            if not groups:
                logger.warning(
                    f"No groups found for study {study_code}. "
                    f"Create groups first with: python manage.py sync_study_roles --study {study_code}"
                )
                return stats
            
            # Build permission map
            permission_map = cls._build_permission_map(app_label)
            
            if not permission_map:
                logger.debug(f"No permissions found for {app_label}")
                return stats
            
            # Assign permissions to each group
            for role_key, group in groups.items():
                # Clear existing permissions if force=True
                if force:
                    study_perms = list(group.permissions.filter(
                        content_type__app_label=app_label
                    ))
                    
                    if study_perms:
                        group.permissions.remove(*study_perms)
                        stats['permissions_removed'] += len(study_perms)
                
                # Get allowed actions for this role
                allowed_actions = RoleTemplate.get_permissions(role_key)
                
                # Collect permissions to assign
                permissions_to_assign = set()
                for model_name, actions_map in permission_map.items():
                    for action in allowed_actions:
                        if action in actions_map:
                            permissions_to_assign.add(actions_map[action])
                
                # Assign permissions in bulk
                if permissions_to_assign:
                    group.permissions.add(*permissions_to_assign)
                    stats['permissions_assigned'] += len(permissions_to_assign)
                    stats['groups_updated'] += 1
                    logger.debug(
                        f"Assigned {len(permissions_to_assign)} permissions to {group.name}"
                    )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error assigning permissions for {study_code}: {e}")
            return stats
    
    @classmethod
    @transaction.atomic
    def initialize_study(cls, study_code: str, force: bool = False) -> Dict[str, any]:
        """
        Complete initialization of study groups and permissions
        
        IMPROVED: Better error handling and clear feedback
        """
        logger.debug(f"Initializing roles for study {study_code}")
        
        # Check prerequisites
        ready, error_msg = cls._check_prerequisites()
        if not ready:
            logger.debug(f"Cannot initialize {study_code}: {error_msg}")
            return {
                'study_code': study_code,
                'error': error_msg,
            }
        
        try:
            # Create groups
            groups = cls.create_study_groups(study_code, force=force)
            
            if not groups:
                return {
                    'study_code': study_code,
                    'error': 'Failed to create groups',
                }
            
            # Assign permissions
            perm_stats = cls.assign_permissions(study_code, force=force)
            
            # Clear cache
            cls.clear_study_cache(study_code)
            
            result = {
                'study_code': study_code,
                'groups_created': len(groups),
                'groups_updated': perm_stats['groups_updated'],
                'permissions_assigned': perm_stats['permissions_assigned'],
                'permissions_removed': perm_stats['permissions_removed'],
                'models_found': perm_stats['models_found'],
            }
            
            if perm_stats['models_found'] > 0:
                logger.info(
                    f"Study {study_code} initialized: "
                    f"{len(groups)} groups, "
                    f"{perm_stats['permissions_assigned']} permissions"
                )
            else:
                logger.debug(
                    f"Study {study_code} groups created. "
                    f"Run migrations to assign permissions."
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error initializing study {study_code}: {e}")
            return {
                'study_code': study_code,
                'error': str(e),
            }
    
    @classmethod
    def get_study_groups(cls, study_code: str, use_cache: bool = True) -> List[Group]:
        """
        Get all groups for a study
        
        IMPROVED: Safe handling when groups don't exist
        """
        if not DatabaseReadinessChecker.are_auth_tables_ready():
            return []
        
        cache_key = f'study_groups_{study_code}'
        
        if use_cache:
            groups = cache.get(cache_key)
            if groups is not None:
                return groups
        
        try:
            group_names = [
                cls.get_group_name(study_code, role_key)
                for role_key in RoleTemplate.get_all_role_keys()
            ]
            groups = list(Group.objects.filter(name__in=group_names))
            
            if use_cache:
                cache.set(cache_key, groups, cls.CACHE_TTL)
            
            return groups
            
        except Exception as e:
            logger.debug(f"Error getting groups for {study_code}: {e}")
            return []
    
    @classmethod
    def get_group_permissions(cls, group: Group, use_cache: bool = True) -> Set[str]:
        """
        Get all permission codenames for a group
        
        IMPROVED: Safe handling
        """
        if not group:
            return set()
        
        cache_key = f'group_perms_{group.id}'
        
        if use_cache:
            perms = cache.get(cache_key)
            if perms is not None:
                return perms
        
        try:
            perms = set(group.permissions.values_list('codename', flat=True))
            
            if use_cache:
                cache.set(cache_key, perms, cls.CACHE_TTL)
            
            return perms
            
        except Exception as e:
            logger.debug(f"Error getting permissions for group {group.name}: {e}")
            return set()
    
    @classmethod
    def validate_group_permissions(cls, study_code: str) -> Dict[str, List[str]]:
        """Validate that groups have correct permissions"""
        if not DatabaseReadinessChecker.are_auth_tables_ready():
            return {'error': ['Auth tables not ready']}
        
        issues = {}
        app_label = f'study_{study_code.lower()}'
        
        try:
            groups = cls.get_study_groups(study_code, use_cache=False)
            permission_map = cls._build_permission_map(app_label)
            
            for group in groups:
                _, role_key = cls.parse_group_name(group.name)
                if not role_key:
                    continue
                
                # Get expected permissions
                allowed_actions = RoleTemplate.get_permissions(role_key)
                expected = set()
                
                for model_name, actions_map in permission_map.items():
                    for action in allowed_actions:
                        if action in actions_map:
                            expected.add(actions_map[action].codename)
                
                # Get actual permissions (only for this study)
                actual = set(
                    group.permissions.filter(
                        content_type__app_label=app_label
                    ).values_list('codename', flat=True)
                )
                
                # Find discrepancies
                missing = expected - actual
                extra = actual - expected
                
                if missing or extra:
                    issues[group.name] = []
                    if missing:
                        issues[group.name].append(f"Missing: {', '.join(sorted(missing))}")
                    if extra:
                        issues[group.name].append(f"Extra: {', '.join(sorted(extra))}")
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating permissions for {study_code}: {e}")
            return {'error': [str(e)]}
    
    @classmethod
    @transaction.atomic
    def sync_all_studies(cls, force: bool = False) -> Dict[str, Dict]:
        """
        Sync permissions for all existing studies
        
        IMPROVED: Checks if tenancy is ready first
        """
        if not DatabaseReadinessChecker.is_tenancy_ready():
            logger.debug("Tenancy tables not ready. Run migrations first.")
            return {}
        
        try:
            from backends.tenancy.models import Study
            
            results = {}
            studies = Study.objects.filter(
                status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
            )
            
            for study in studies:
                try:
                    result = cls.initialize_study(study.code, force=force)
                    results[study.code] = result
                except Exception as e:
                    logger.error(f"Error syncing study {study.code}: {e}")
                    results[study.code] = {'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Error syncing all studies: {e}")
            return {}
    
    @classmethod
    def clear_study_cache(cls, study_code: str):
        """Clear all cached data for a study"""
        cache.delete(f'study_groups_{study_code}')
        
        prefix = f"Study {study_code.upper()}."
        
        try:
            groups = Group.objects.filter(name__startswith=prefix)
            for group in groups:
                cache.delete(f'group_perms_{group.id}')
        except Exception:
            pass
        
        logger.debug(f"Cleared cache for study {study_code}")
    
    @classmethod
    @transaction.atomic
    def delete_study_groups(cls, study_code: str) -> int:
        """Delete all groups for a study"""
        if not DatabaseReadinessChecker.are_auth_tables_ready():
            return 0
        
        try:
            group_names = [
                cls.get_group_name(study_code, role_key)
                for role_key in RoleTemplate.get_all_role_keys()
            ]
            
            deleted, _ = Group.objects.filter(name__in=group_names).delete()
            cls.clear_study_cache(study_code)
            
            if deleted > 0:
                logger.warning(f"Deleted {deleted} groups for study {study_code}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting groups for {study_code}: {e}")
            return 0
    
    @classmethod
    def get_statistics(cls) -> Dict[str, any]:
        """Get overall statistics about study groups"""
        if not DatabaseReadinessChecker.is_tenancy_ready():
            return {
                'error': 'Tenancy tables not ready',
                'message': 'Run: python manage.py migrate',
            }
        
        try:
            from backends.tenancy.models import Study
            
            total_studies = Study.objects.filter(
                status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
            ).count()
            
            total_groups = 0
            for display_name in RoleTemplate.get_all_display_names():
                total_groups += Group.objects.filter(
                    name__startswith="Study ",
                    name__endswith=f".{display_name}"
                ).count()
            
            expected_groups = total_studies * len(RoleTemplate.get_all_role_keys())
            
            return {
                'total_studies': total_studies,
                'total_groups': total_groups,
                'expected_groups': expected_groups,
                'missing_groups': max(0, expected_groups - total_groups),
                'role_templates': len(RoleTemplate.get_all_role_keys()),
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def initialize_study_roles(study_code: str, force: bool = False) -> Dict:
    """Initialize roles and permissions for a study"""
    return StudyRoleManager.initialize_study(study_code, force=force)


def sync_study_permissions(study_code: str) -> Dict:
    """Sync permissions without recreating groups"""
    return StudyRoleManager.assign_permissions(study_code, force=True)


def validate_study_roles(study_code: str) -> Dict:
    """Validate that study roles have correct permissions"""
    return StudyRoleManager.validate_group_permissions(study_code)


def get_available_role_keys() -> List[str]:
    """Get all role keys"""
    return RoleTemplate.get_all_role_keys()


def get_available_display_names() -> List[str]:
    """Get all display names"""
    return RoleTemplate.get_all_display_names()


def convert_key_to_display(role_key: str) -> str:
    """Convert role_key to display_name"""
    return RoleTemplate.get_display_name(role_key)


def convert_display_to_key(display_name: str) -> Optional[str]:
    """Convert display_name to role_key"""
    return RoleTemplate.get_role_key(display_name)


def get_role_description(role_key: str) -> Optional[str]:
    """Get role description"""
    return RoleTemplate.get_description(role_key)


def parse_group_to_role_key(group_name: str) -> Optional[str]:
    """Parse group name to get role_key"""
    _, role_key = StudyRoleManager.parse_group_name(group_name)
    return role_key