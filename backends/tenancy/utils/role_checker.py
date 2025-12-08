# backend/tenancy/utils/role_checker.py - IMPROVED WITH GRACEFUL ERROR HANDLING
"""
RoleChecker - Simplified role verification utility

IMPROVED:
- Graceful handling when database isn't ready
- Better error messages and logging
- Safe operations during initial setup
- Returns None/empty instead of crashing

Usage Examples:
    >>> from backends.tenancy.utils import RoleChecker
    >>> 
    >>> # Check if user is admin in study
    >>> RoleChecker.is_admin(user, study)
    True
    >>> 
    >>> # Get user's role
    >>> RoleChecker.get_role(user, study)
    'data_manager'
"""
from typing import Optional, Set, Dict, List, Any
from django.db.utils import OperationalError 
import logging

logger = logging.getLogger(__name__)


# ==========================================
# DATABASE SAFETY WRAPPER
# ==========================================

class SafeQueryWrapper:
    """
    Wrapper for safe database queries
    Returns None/empty on error instead of crashing
    """
    
    @staticmethod
    def safe_query(func, default=None, log_error=True):
        """
        Execute a function safely, catching database errors
        
        Args:
            func: Function to execute
            default: Default value to return on error
            log_error: Whether to log errors
            
        Returns:
            Function result or default value
        """
        try:
            return func()
        except OperationalError as e:
            if log_error:
                logger.debug(f"Database not ready: {e}")
            return default
        except ImportError as e:
            if log_error:
                logger.debug(f"Models not imported yet: {e}")
            return default
        except Exception as e:
            if log_error:
                logger.debug(f"Query error: {e}")
            return default


# ==========================================
# ROLE CHECKER (IMPROVED)
# ==========================================

class RoleChecker:
    """
    Utility class for easy role and permission checking
    
    IMPROVED:
    - All methods return safely (no crashes)
    - Graceful handling when database isn't ready
    - Clear logging for troubleshooting
    """
    
    CACHE_TTL = 300  # 5 minutes
    
    # ==========================================
    # ROLE VERIFICATION
    # ==========================================
    
    @staticmethod
    def get_role(user, study) -> Optional[str]:
        """
        Get user's role key in a study
        
        IMPROVED: Safe handling when database not ready
        
        Returns:
            Role key (e.g., 'data_manager') or None
        """
        if not user or not study:
            return None
        
        def _query():
            if hasattr(user, 'get_study_role'):
                return user.get_study_role(study)
            
            # Fallback
            from backends.tenancy.models import StudyMembership
            
            membership = StudyMembership.objects.select_related('group').filter(
                user=user,
                study=study,
                is_active=True
            ).first()
            
            if membership:
                return membership.get_role_key()
            return None
        
        return SafeQueryWrapper.safe_query(_query, default=None, log_error=False)
    
    @staticmethod
    def get_role_display(user, study) -> Optional[str]:
        """
        Get user's role display name in a study
        
        IMPROVED: Safe handling
        
        Returns:
            Display name (e.g., 'Data Manager') or None
        """
        if not user or not study:
            return None
        
        def _query():
            if hasattr(user, 'get_study_role_display'):
                return user.get_study_role_display(study)
            
            from backends.tenancy.models import StudyMembership
            
            membership = StudyMembership.objects.select_related('group').filter(
                user=user,
                study=study,
                is_active=True
            ).first()
            
            if membership:
                return membership.get_role_display_name()
            return None
        
        return SafeQueryWrapper.safe_query(_query, default=None, log_error=False)
    
    @staticmethod
    def has_role(user, study, role_key: str) -> bool:
        """
        Check if user has specific role in a study
        
        IMPROVED: Safe, returns False on error
        """
        if not user or not study or not role_key:
            return False
        
        current_role = RoleChecker.get_role(user, study)
        return current_role == role_key if current_role else False
    
    @staticmethod
    def is_admin(user, study) -> bool:
        """
        Check if user is admin (has privileged role)
        
        IMPROVED: Safe, returns False on error
        """
        if not user or not study:
            return False
        
        role_key = RoleChecker.get_role(user, study)
        if not role_key:
            return False
        
        def _query():
            from backends.tenancy.utils.role_manager import RoleTemplate
            
            config = RoleTemplate.get_role_config(role_key)
            return config.get('is_privileged', False) if config else False
        
        result = SafeQueryWrapper.safe_query(_query, default=False, log_error=False)
        return bool(result) if result is not None else False
    
    # ==========================================
    # QUICK ROLE CHECKS
    # ==========================================
    
    @staticmethod
    def is_data_manager(user, study) -> bool:
        """Check if user is Data Manager"""
        return RoleChecker.has_role(user, study, 'data_manager')
    
    @staticmethod
    def is_research_manager(user, study) -> bool:
        """Check if user is Research Manager"""
        return RoleChecker.has_role(user, study, 'research_manager')
    
    @staticmethod
    def is_principal_investigator(user, study) -> bool:
        """Check if user is Principal Investigator"""
        return RoleChecker.has_role(user, study, 'principal_investigator')
    
    @staticmethod
    def is_research_monitor(user, study) -> bool:
        """Check if user is Research Monitor"""
        return RoleChecker.has_role(user, study, 'research_monitor')
    
    @staticmethod
    def is_research_staff(user, study) -> bool:
        """Check if user is Research Staff"""
        return RoleChecker.has_role(user, study, 'research_staff')
    
    # ==========================================
    # PERMISSION CHECKS
    # ==========================================
    
    @staticmethod
    def can(user, study, permission_codename: str) -> bool:
        """
        Check if user has specific permission
        
        IMPROVED: Safe, returns False on error
        """
        if not user or not study or not permission_codename:
            return False
        
        def _query():
            from backends.tenancy.utils import TenancyUtils
            return TenancyUtils.user_has_permission(user, study, permission_codename)
        
        result = SafeQueryWrapper.safe_query(_query, default=False, log_error=False)
        return bool(result) if result is not None else False
    
    @staticmethod
    def can_add(user, study, model_name: str) -> bool:
        """Check if user can add records for a model"""
        return RoleChecker.can(user, study, f'add_{model_name}')
    
    @staticmethod
    def can_change(user, study, model_name: str) -> bool:
        """Check if user can change records"""
        return RoleChecker.can(user, study, f'change_{model_name}')
    
    @staticmethod
    def can_delete(user, study, model_name: str) -> bool:
        """Check if user can delete records"""
        return RoleChecker.can(user, study, f'delete_{model_name}')
    
    @staticmethod
    def can_view(user, study, model_name: str) -> bool:
        """Check if user can view records"""
        return RoleChecker.can(user, study, f'view_{model_name}')
    
    # ==========================================
    # QUICK PERMISSION CHECKS
    # ==========================================
    
    @staticmethod
    def can_add_patients(user, study) -> bool:
        """Quick check: can add patients"""
        return RoleChecker.can_add(user, study, 'patient')
    
    @staticmethod
    def can_edit_patients(user, study) -> bool:
        """Quick check: can edit patients"""
        return RoleChecker.can_change(user, study, 'patient')
    
    @staticmethod
    def can_delete_patients(user, study) -> bool:
        """Quick check: can delete patients"""
        return RoleChecker.can_delete(user, study, 'patient')
    
    @staticmethod
    def can_view_patients(user, study) -> bool:
        """Quick check: can view patients"""
        return RoleChecker.can_view(user, study, 'patient')
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    
    @staticmethod
    def get_all_permissions(user, study) -> Set[str]:
        """
        Get all permissions for user in study
        
        IMPROVED: Returns empty set on error
        """
        if not user or not study:
            return set()
        
        def _query():
            from backends.tenancy.utils import TenancyUtils
            return TenancyUtils.get_user_permissions(user, study)
        
        result = SafeQueryWrapper.safe_query(_query, default=set(), log_error=False)
        return result if result is not None else set()
    
    @staticmethod
    def get_permission_summary(user, study) -> Dict[str, List[str]]:
        """
        Get permissions organized by model
        
        IMPROVED: Returns empty dict on error
        """
        if not user or not study:
            return {}
        
        def _query():
            from backends.tenancy.utils import TenancyUtils
            return TenancyUtils.get_permission_display(user, study)
        
        result = SafeQueryWrapper.safe_query(_query, default={}, log_error=False)
        return result if result is not None else {}
    
    @staticmethod
    def get_all_user_roles(user) -> Dict[int, Dict[str, str]]:
        """
        Get all roles across all studies for a user
        
        IMPROVED: Returns empty dict on error
        """
        if not user:
            return {}
        
        def _query():
            if hasattr(user, 'get_all_study_roles'):
                return user.get_all_study_roles()
            
            from backends.tenancy.models import StudyMembership
            
            memberships = StudyMembership.objects.filter(
                user=user,
                is_active=True
            ).select_related('study', 'group')
            
            result = {}
            for membership in memberships:
                result[membership.study.id] = {
                    'study_code': membership.study.code,
                    'study_name': membership.study.safe_translation_getter('name', any_language=True),
                    'role_key': membership.get_role_key(),
                    'role_name': membership.get_role_display_name(),
                }
            
            return result
        
        result = SafeQueryWrapper.safe_query(_query, default={}, log_error=False)
        return result if result is not None else {}
    
    # ==========================================
    # COMPARISON & VALIDATION
    # ==========================================
    
    @staticmethod
    def compare_roles(role_key_1: str, role_key_2: str) -> Dict[str, Any]:
        """
        Compare two roles
        
        IMPROVED: Safe handling
        """
        if not role_key_1 or not role_key_2:
            return {'error': 'Invalid role keys'}
        
        def _query():
            from backends.tenancy.utils.role_manager import RoleTemplate
            
            config_1 = RoleTemplate.get_role_config(role_key_1)
            config_2 = RoleTemplate.get_role_config(role_key_2)
            
            if not config_1 or not config_2:
                return {'error': 'Invalid role key(s)'}
            
            perms_1 = set(config_1.get('permissions', []))
            perms_2 = set(config_2.get('permissions', []))
            
            return {
                'role_1': role_key_1,
                'role_1_display': config_1.get('display_name'),
                'role_2': role_key_2,
                'role_2_display': config_2.get('display_name'),
                'role_1_permissions': list(perms_1),
                'role_2_permissions': list(perms_2),
                'role_1_has_more': len(perms_1) > len(perms_2),
                'additional_permissions': list(perms_1 - perms_2),
                'missing_permissions': list(perms_2 - perms_1),
                'common_permissions': list(perms_1 & perms_2),
                'priority_diff': config_1.get('priority', 0) - config_2.get('priority', 0),
                'role_1_privileged': config_1.get('is_privileged', False),
                'role_2_privileged': config_2.get('is_privileged', False),
            }
        
        result = SafeQueryWrapper.safe_query(
            _query, 
            default={'error': 'Query failed'}, 
            log_error=True
        )
        return result if result is not None else {'error': 'Query failed'}
    
    @staticmethod
    def validate_role_change(user, study, new_role_key: str) -> Dict[str, Any]:
        """
        Validate if changing to a new role is valid
        
        IMPROVED: Safe handling
        """
        if not user or not study or not new_role_key:
            return {'valid': False, 'error': 'Invalid parameters'}
        
        def _query():
            from backends.tenancy.utils.role_manager import RoleTemplate
            
            current_role = RoleChecker.get_role(user, study)
            
            if not current_role:
                return {
                    'valid': False,
                    'error': 'User has no current role in this study'
                }
            
            new_config = RoleTemplate.get_role_config(new_role_key)
            if not new_config:
                return {
                    'valid': False,
                    'error': f'Invalid role key: {new_role_key}'
                }
            
            comparison = RoleChecker.compare_roles(current_role, new_role_key)
            
            if 'error' in comparison:
                return {'valid': False, 'error': comparison['error']}
            
            return {
                'valid': True,
                'current_role': current_role,
                'current_display': comparison['role_1_display'],
                'new_role': new_role_key,
                'new_display': comparison['role_2_display'],
                'is_downgrade': comparison['priority_diff'] > 0,
                'is_upgrade': comparison['priority_diff'] < 0,
                'permissions_gained': comparison['missing_permissions'],
                'permissions_lost': comparison['additional_permissions'],
                'privilege_change': (
                    comparison['role_1_privileged'] and not comparison['role_2_privileged']
                ),
            }
        
        result = SafeQueryWrapper.safe_query(
            _query,
            default={'valid': False, 'error': 'Query failed'},
            log_error=True
        )
        return result if result is not None else {'valid': False, 'error': 'Query failed'}
    
    # ==========================================
    # DEBUGGING & UTILITIES
    # ==========================================
    
    @staticmethod
    def print_user_info(user, study):
        """
        Print comprehensive user role and permission info
        
        IMPROVED: Safe printing
        """
        if not user or not study:
            print("Invalid user or study")
            return
        
        print("\n" + "=" * 70)
        print(f"USER ROLE INFORMATION")
        print("=" * 70)
        
        # User info
        username = getattr(user, 'username', 'Unknown')
        full_name = getattr(user, 'get_full_name', lambda: 'Unknown')()
        print(f"User: {username} ({full_name})")
        
        # Study info
        study_code = getattr(study, 'code', 'Unknown')
        print(f"Study: {study_code}")
        
        is_active = getattr(user, 'is_active', None)
        print(f"Active: {is_active}")
        print()
        
        # Role info
        role_key = RoleChecker.get_role(user, study)
        role_display = RoleChecker.get_role_display(user, study)
        
        print(f"Role Key: {role_key or 'None'}")
        print(f"Role Display: {role_display or 'None'}")
        print(f"Is Admin: {RoleChecker.is_admin(user, study)}")
        print()
        
        # Permissions
        print("PERMISSIONS BY MODEL:")
        summary = RoleChecker.get_permission_summary(user, study)
        
        if summary:
            for model, actions in sorted(summary.items()):
                print(f"  {model:20s}: {', '.join(sorted(actions))}")
        else:
            print("  No permissions found (database may not be ready)")
        
        print()
        all_perms = RoleChecker.get_all_permissions(user, study)
        print(f"Total Permissions: {len(all_perms)}")
        print("=" * 70 + "\n")
    
    @staticmethod
    def get_role_hierarchy() -> List[Dict[str, Any]]:
        """
        Get all roles sorted by priority
        
        IMPROVED: Safe handling
        """
        def _query():
            from backends.tenancy.utils.role_manager import RoleTemplate
            
            roles = []
            for role_key in RoleTemplate.get_all_role_keys():
                config = RoleTemplate.get_role_config(role_key)
                if config:
                    roles.append({
                        'role_key': role_key,
                        'display_name': config.get('display_name'),
                        'description': config.get('description'),
                        'priority': config.get('priority', 0),
                        'is_privileged': config.get('is_privileged', False),
                        'permissions': config.get('permissions', []),
                    })
            
            # Sort by priority (highest first)
            roles.sort(key=lambda x: x['priority'], reverse=True)
            return roles
        
        result = SafeQueryWrapper.safe_query(_query, default=[], log_error=True)
        return result if result is not None else []


# ==========================================
# CONVENIENCE SHORTCUTS
# ==========================================

def get_user_role(user, study) -> Optional[str]:
    """Shortcut: Get user's role in study"""
    return RoleChecker.get_role(user, study)


def check_permission(user, study, permission: str) -> bool:
    """Shortcut: Check if user has permission"""
    return RoleChecker.can(user, study, permission)


def is_study_admin(user, study) -> bool:
    """Shortcut: Check if user is admin"""
    return RoleChecker.is_admin(user, study)


def print_user_permissions(user, study):
    """Shortcut: Print user info"""
    RoleChecker.print_user_info(user, study)