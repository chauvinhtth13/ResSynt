"""
Role Checker - Simplified role verification utility.

All methods return safely (no crashes) with graceful error handling.
"""
import logging
from typing import Any, Dict, List, Optional, Set

from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


def safe_query(func, default=None):
    """Execute function safely, returning default on error."""
    try:
        return func()
    except (OperationalError, ImportError, Exception) as e:
        logger.debug(f"Safe query caught: {type(e).__name__}")
        return default


class RoleChecker:
    """
    Role and permission verification utility.
    
    All methods are safe - they return None/False/empty on errors
    instead of raising exceptions.
    """
    
    # =========================================================================
    # Role Verification
    # =========================================================================
    
    @staticmethod
    def get_role(user, study) -> Optional[str]:
        """Get user's role key in a study."""
        if not user or not study:
            return None
        
        def _query():
            if hasattr(user, 'get_study_role'):
                return user.get_study_role(study)
            
            from backends.tenancy.models import StudyMembership
            membership = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            ).select_related('group').first()
            
            return membership.get_role_key() if membership else None
        
        return safe_query(_query)
    
    @staticmethod
    def get_role_display(user, study) -> Optional[str]:
        """Get user's role display name in a study."""
        if not user or not study:
            return None
        
        def _query():
            if hasattr(user, 'get_study_role_display'):
                return user.get_study_role_display(study)
            
            from backends.tenancy.models import StudyMembership
            membership = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            ).select_related('group').first()
            
            return membership.get_role_display_name() if membership else None
        
        return safe_query(_query)
    
    @staticmethod
    def has_role(user, study, role_key: str) -> bool:
        """Check if user has specific role in a study."""
        if not user or not study or not role_key:
            return False
        return RoleChecker.get_role(user, study) == role_key
    
    @staticmethod
    def is_admin(user, study) -> bool:
        """Check if user has admin/privileged role."""
        if not user or not study:
            return False
        
        role_key = RoleChecker.get_role(user, study)
        if not role_key:
            return False
        
        def _query():
            from .role_manager import RoleTemplate
            config = RoleTemplate.get_role_config(role_key)
            return config.get('is_privileged', False) if config else False
        
        return safe_query(_query, default=False) or False
    
    # =========================================================================
    # Quick Role Checks
    # =========================================================================
    
    @staticmethod
    def is_data_manager(user, study) -> bool:
        return RoleChecker.has_role(user, study, 'data_manager')
    
    @staticmethod
    def is_research_manager(user, study) -> bool:
        return RoleChecker.has_role(user, study, 'research_manager')
    
    @staticmethod
    def is_principal_investigator(user, study) -> bool:
        return RoleChecker.has_role(user, study, 'principal_investigator')
    
    @staticmethod
    def is_research_monitor(user, study) -> bool:
        return RoleChecker.has_role(user, study, 'research_monitor')
    
    @staticmethod
    def is_research_staff(user, study) -> bool:
        return RoleChecker.has_role(user, study, 'research_staff')
    
    # =========================================================================
    # Permission Checks
    # =========================================================================
    
    @staticmethod
    def can(user, study, permission_codename: str) -> bool:
        """Check if user has specific permission."""
        if not user or not study or not permission_codename:
            return False
        
        def _query():
            from .tenancy_utils import TenancyUtils
            permissions = TenancyUtils.get_user_permissions(user, study)
            return permission_codename in permissions
        
        return safe_query(_query, default=False) or False
    
    @staticmethod
    def can_any(user, study, permission_codenames: List[str]) -> bool:
        """Check if user has any of the permissions."""
        if not user or not study or not permission_codenames:
            return False
        
        def _query():
            from .tenancy_utils import TenancyUtils
            permissions = TenancyUtils.get_user_permissions(user, study)
            return bool(permissions & set(permission_codenames))
        
        return safe_query(_query, default=False) or False
    
    @staticmethod
    def can_all(user, study, permission_codenames: List[str]) -> bool:
        """Check if user has all permissions."""
        if not user or not study or not permission_codenames:
            return False
        
        def _query():
            from .tenancy_utils import TenancyUtils
            permissions = TenancyUtils.get_user_permissions(user, study)
            return set(permission_codenames).issubset(permissions)
        
        return safe_query(_query, default=False) or False
    
    @staticmethod
    def get_all_permissions(user, study) -> Set[str]:
        """Get all permission codenames for user in study."""
        if not user or not study:
            return set()
        
        def _query():
            from .tenancy_utils import TenancyUtils
            return TenancyUtils.get_user_permissions(user, study)
        
        return safe_query(_query, default=set()) or set()
    
    @staticmethod
    def get_permission_summary(user, study) -> Dict[str, List[str]]:
        """Get permissions grouped by model."""
        if not user or not study:
            return {}
        
        def _query():
            from .tenancy_utils import TenancyUtils
            return TenancyUtils.get_permission_display(user, study)
        
        return safe_query(_query, default={}) or {}
    
    # =========================================================================
    # User Studies
    # =========================================================================
    
    @staticmethod
    def get_user_roles_in_all_studies(user) -> Dict[int, Dict[str, Any]]:
        """Get user's roles in all studies."""
        if not user:
            return {}
        
        def _query():
            from backends.tenancy.models import StudyMembership
            
            memberships = StudyMembership.objects.filter(
                user=user, is_active=True
            ).select_related('study', 'group')
            
            return {
                m.study.id: {
                    'study_code': m.study.code,
                    'role_key': m.get_role_key(),
                    'role_name': m.get_role_display_name(),
                }
                for m in memberships
            }
        
        return safe_query(_query, default={}) or {}
    
    # =========================================================================
    # Role Hierarchy
    # =========================================================================
    
    @staticmethod
    def get_role_hierarchy() -> List[Dict[str, Any]]:
        """Get all roles sorted by priority."""
        def _query():
            from .role_manager import RoleTemplate
            
            roles = []
            for role_key in RoleTemplate.get_all_role_keys():
                config = RoleTemplate.get_role_config(role_key)
                if config:
                    roles.append({
                        'role_key': role_key,
                        'display_name': config.get('display_name'),
                        'priority': config.get('priority', 0),
                        'is_privileged': config.get('is_privileged', False),
                    })
            
            roles.sort(key=lambda x: x['priority'], reverse=True)
            return roles
        
        return safe_query(_query, default=[]) or []


# =============================================================================
# Convenience Functions
# =============================================================================

def get_user_role(user, study) -> Optional[str]:
    return RoleChecker.get_role(user, study)


def check_permission(user, study, permission: str) -> bool:
    return RoleChecker.can(user, study, permission)


def is_study_admin(user, study) -> bool:
    return RoleChecker.is_admin(user, study)