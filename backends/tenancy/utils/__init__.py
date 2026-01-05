# backend/tenancy/utils/__init__.py
"""
Tenancy utilities package
"""

# Core utilities
from .tenancy_utils import (
    TenancyUtils,
    validate_study_code,
    validate_database_name,
    validate_site_code,
    validate_username,
    validate_email,
    validate_permission_code,
    validate_schema_name,
    get_model_permissions,
    get_all_study_permissions,
    create_custom_permission,
)

# Role management
from .role_manager import (
    StudyRoleManager,
    RoleTemplate,
    initialize_study_roles,
    sync_study_permissions,
    validate_study_roles,
    get_available_role_keys,
    get_available_display_names,
    convert_key_to_display,
    convert_display_to_key,
    get_role_description,
    parse_group_to_role_key,
)

# Role checker
from .role_checker import (
    RoleChecker,
    get_user_role,
    check_permission,
    is_study_admin,
    print_user_permissions,
)

# Database utilities
from .db_study_creator import DatabaseStudyCreator

__all__ = [
    # Core utilities
    'TenancyUtils',
    'validate_study_code',
    'validate_database_name',
    'validate_site_code',
    'validate_username',
    'validate_email',
    'validate_permission_code',
    'validate_schema_name',
    'get_model_permissions',
    'get_all_study_permissions',
    'create_custom_permission',
    
    # Role management
    'StudyRoleManager',
    'RoleTemplate',
    'initialize_study_roles',
    'sync_study_permissions',
    'validate_study_roles',
    'get_available_role_keys',
    'get_available_display_names',
    'convert_key_to_display',
    'convert_display_to_key',
    'get_role_description',
    'parse_group_to_role_key',
    
    #  NEW: Role checker
    'RoleChecker',
    'get_user_role',
    'check_permission',
    'is_study_admin',
    'print_user_permissions',
    
    # Database utilities
    'DatabaseStudyCreator',
]