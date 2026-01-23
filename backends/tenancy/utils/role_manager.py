"""
Study Role Management System.

Manages Django Groups and Permissions for study apps with:
- Automatic permission assignment based on role templates
- Graceful handling when database isn't ready
- Caching for performance
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection, transaction
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


# =============================================================================
# Database Readiness
# =============================================================================

def is_db_ready() -> bool:
    """Check if database tables are ready."""
    try:
        Group.objects.exists()
        return True
    except (OperationalError, Exception):
        return False


def is_contenttypes_ready() -> bool:
    """Check if ContentType tables are ready."""
    try:
        ContentType.objects.exists()
        return True
    except (OperationalError, Exception):
        return False


# =============================================================================
# Role Templates
# =============================================================================

class RoleTemplate:
    """Define role templates with permission patterns."""
    
    ROLES = {
        "data_manager": {
            "display_name": "Data Manager",
            "description": "Full study access including user management.",
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
            "description": "Leads the study with view access.",
            "permissions": ["view"],
            "priority": 70,
            "is_privileged": False,
        },
        "research_monitor": {
            "display_name": "Research Monitor",
            "description": "Conducts study monitoring and review.",
            "permissions": ["view"],
            "priority": 60,
            "is_privileged": False,
        },
        "research_staff": {
            "display_name": "Research Staff",
            "description": "Performs data entry and follow-up.",
            "permissions": ["add", "change", "view"],
            "priority": 50,
            "is_privileged": False,
        },
    }
    
    _DISPLAY_MAP = {v["display_name"]: k for k, v in ROLES.items()}
    
    @classmethod
    def get_all_role_keys(cls) -> List[str]:
        return list(cls.ROLES.keys())
    
    @classmethod
    def get_all_display_names(cls) -> List[str]:
        return [r["display_name"] for r in cls.ROLES.values()]
    
    @classmethod
    def get_role_config(cls, role_key: str) -> Optional[Dict]:
        return cls.ROLES.get(role_key)
    
    @classmethod
    def get_display_name(cls, role_key: str) -> str:
        config = cls.get_role_config(role_key)
        return config["display_name"] if config else role_key
    
    @classmethod
    def get_role_key(cls, display_name: str) -> Optional[str]:
        return cls._DISPLAY_MAP.get(display_name)
    
    @classmethod
    def get_permissions(cls, role_key: str) -> List[str]:
        config = cls.get_role_config(role_key)
        return config.get("permissions", []) if config else []
    
    @classmethod
    def is_valid_role_key(cls, role_key: str) -> bool:
        return role_key in cls.ROLES


# =============================================================================
# Study Role Manager
# =============================================================================

class StudyRoleManager:
    """Manages study-specific roles and permissions."""
    
    CACHE_TTL = 600
    
    @classmethod
    def get_group_name(cls, study_code: str, role_key: str) -> str:
        """Generate study-specific group name."""
        display_name = RoleTemplate.get_display_name(role_key)
        return f"Study {study_code.upper()}.{display_name}"
    
    @classmethod
    def parse_group_name(cls, group_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse group name to extract study_code and role_key."""
        if not group_name.startswith("Study "):
            return None, None
        
        parts = group_name[6:].split('.', 1)
        if len(parts) != 2:
            return None, None
        
        study_code, display_name = parts
        role_key = RoleTemplate.get_role_key(display_name)
        return (study_code, role_key) if role_key else (None, None)
    
    @classmethod
    def is_study_group(cls, group_name: str) -> bool:
        """Check if group name follows study group naming convention."""
        if not group_name or not isinstance(group_name, str):
            return False
        return group_name.startswith("Study ")
    
    @classmethod
    @transaction.atomic
    def initialize_study(cls, study_code: str, force: bool = False) -> Dict[str, Any]:
        """Initialize groups and permissions for a study."""
        if not is_db_ready():
            return {'error': 'Database not ready. Run migrations first.'}
        
        result = {
            'groups_created': 0,
            'permissions_assigned': 0,
            'study_code': study_code,
        }
        
        try:
            # Create groups
            groups = cls.create_study_groups(study_code, force)
            result['groups_created'] = len([g for g in groups.values() if g])
            
            # Assign permissions
            perm_result = cls.assign_permissions(study_code, force)
            result['permissions_assigned'] = perm_result.get('permissions_assigned', 0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error initializing study {study_code}: {type(e).__name__}")
            return {'error': str(e)}
    
    @classmethod
    @transaction.atomic
    def create_study_groups(cls, study_code: str, force: bool = False) -> Dict[str, Optional[Group]]:
        """Create all groups for a study."""
        if not is_db_ready():
            return {}
        
        groups = {}
        for role_key in RoleTemplate.get_all_role_keys():
            group_name = cls.get_group_name(study_code, role_key)
            
            if force:
                Group.objects.filter(name=group_name).delete()
            
            group, _ = Group.objects.get_or_create(name=group_name)
            groups[role_key] = group
        
        return groups
    
    @classmethod
    def get_study_groups(cls, study_code: str) -> List[Group]:
        """Get all groups for a study."""
        cache_key = f'study_groups_{study_code}'
        groups = cache.get(cache_key)
        
        if groups is None:
            prefix = f"Study {study_code.upper()}."
            groups = list(Group.objects.filter(name__startswith=prefix))
            cache.set(cache_key, groups, cls.CACHE_TTL)
        
        return groups
    
    @classmethod
    @transaction.atomic
    def assign_permissions(cls, study_code: str, force: bool = False) -> Dict[str, int]:
        """Assign permissions to study groups."""
        stats = {'permissions_assigned': 0, 'permissions_removed': 0}
        
        if not is_db_ready() or not is_contenttypes_ready():
            logger.warning(f"Database not ready for permission assignment: study {study_code}")
            return stats
        
        app_label = f'study_{study_code.lower()}'
        
        # Get all permissions for this study app
        all_permissions = Permission.objects.filter(
            content_type__app_label=app_label
        ).select_related('content_type')
        
        if not all_permissions.exists():
            # This is expected during initial migration when ContentTypes exist
            # but Permission objects haven't been created by auth's post_migrate yet.
            # Django creates permissions in post_migrate signal from django.contrib.auth.
            # Use debug level since this is normal during migration sequence.
            logger.debug(
                f"No permissions found for app_label '{app_label}'. "
                f"This is normal if migrations are still running. "
                f"Permissions will be synced after all migrations complete."
            )
            return stats
        
        logger.debug(f"Found {all_permissions.count()} permissions for {app_label}")
        
        # Build permission map: {model: {action: permission}}
        perm_map: Dict[str, Dict[str, Permission]] = {}
        for perm in all_permissions:
            model = perm.content_type.model
            action = perm.codename.split('_')[0]
            perm_map.setdefault(model, {})[action] = perm
        
        # Get groups and assign permissions
        groups = cls.get_study_groups(study_code)
        
        for group in groups:
            _, role_key = cls.parse_group_name(group.name)
            if not role_key:
                continue
            
            allowed_actions = set(RoleTemplate.get_permissions(role_key))
            
            # Calculate expected permissions
            expected_perms: Set[Permission] = set()
            for model_perms in perm_map.values():
                for action, perm in model_perms.items():
                    if action in allowed_actions:
                        expected_perms.add(perm)
            
            # Get current permissions (only for this app)
            current_perms = set(group.permissions.filter(content_type__app_label=app_label))
            
            # Add missing
            to_add = expected_perms - current_perms
            if to_add:
                group.permissions.add(*to_add)
                stats['permissions_assigned'] += len(to_add)
                logger.info(
                    f"Added {len(to_add)} permissions to group '{group.name}' "
                    f"(role: {role_key}, actions: {allowed_actions})"
                )
            
            # Remove extra (only if force)
            if force:
                to_remove = current_perms - expected_perms
                if to_remove:
                    group.permissions.remove(*to_remove)
                    stats['permissions_removed'] += len(to_remove)
                    logger.info(f"Removed {len(to_remove)} permissions from group '{group.name}'")
        
        # Clear cache
        cls.clear_study_cache(study_code)
        
        return stats
    
    @classmethod
    def get_group_permissions(cls, group: Group) -> Set[str]:
        """Get permission codenames for a group."""
        cache_key = f'group_perms_{group.pk}'
        perms = cache.get(cache_key)
        
        if perms is None:
            perms = set(group.permissions.values_list('codename', flat=True))
            cache.set(cache_key, perms, cls.CACHE_TTL)
        
        return perms
    
    @classmethod
    def clear_study_cache(cls, study_code: str) -> None:
        """Clear cache for a study."""
        cache.delete(f'study_groups_{study_code}')
        
        try:
            for group in cls.get_study_groups(study_code):
                cache.delete(f'group_perms_{group.pk}')
        except Exception:
            pass
    
    @classmethod
    @transaction.atomic
    def delete_study_groups(cls, study_code: str) -> int:
        """Delete all groups for a study."""
        if not is_db_ready():
            return 0
        
        group_names = [
            cls.get_group_name(study_code, role_key)
            for role_key in RoleTemplate.get_all_role_keys()
        ]
        
        deleted, _ = Group.objects.filter(name__in=group_names).delete()
        cls.clear_study_cache(study_code)
        
        if deleted:
            logger.warning(f"Deleted {deleted} groups for study {study_code}")
        
        return deleted


# =============================================================================
# Convenience Functions
# =============================================================================

def initialize_study_roles(study_code: str, force: bool = False) -> Dict:
    return StudyRoleManager.initialize_study(study_code, force)


def sync_study_permissions(study_code: str) -> Dict:
    return StudyRoleManager.assign_permissions(study_code, force=True)


def get_available_role_keys() -> List[str]:
    return RoleTemplate.get_all_role_keys()


def get_available_display_names() -> List[str]:
    return RoleTemplate.get_all_display_names()


def convert_key_to_display(role_key: str) -> str:
    return RoleTemplate.get_display_name(role_key)


def convert_display_to_key(display_name: str) -> Optional[str]:
    return RoleTemplate.get_role_key(display_name)