# backend/api/base/constants.py - FINAL VERSION
"""
Constants for authentication system - PRODUCTION READY

✅ ADDED: Clear documentation of lockout phases
✅ FIXED: Added all cache key constants
✅ IMPROVED: Helper methods for cache key generation
"""
from django.utils.translation import gettext_lazy as _


class LoginMessages:
    """
    Centralized messages for authentication system.
    
    ✅ DOCUMENTED: Progressive Lockout System
    
    With AXES_FAILURE_LIMIT = 7:
    
    Phase 1 (Attempts 1-4):
        - Remaining: 6-3 attempts
        - Message: INVALID_CREDENTIALS
        - Action: Generic error, no warning
        - Status: 200 OK
    
    Phase 2 (Attempts 5-6):
        - Remaining: 2-1 attempts
        - Message: ACCOUNT_WILL_BE_LOCKED (with countdown)
        - Action: Warning user about impending lockout
        - Status: 200 OK
    
    Phase 3 (Attempt 7+):
        - Remaining: 0 attempts
        - Message: ACCOUNT_LOCKED
        - Action: Account locked, form disabled
        - Status: 403 Forbidden
        - Backend: User.is_active = False
        - URL: /login/ (no redirect!)
    """
    
    # Login error messages
    INVALID_CREDENTIALS = _("Invalid login. Try again.")
    ACCOUNT_LOCKED = _("Account locked. Please contact support.")
    ACCOUNT_WILL_BE_LOCKED = _("Login failed. {} attempt(s) remaining before lockout.")
    
    # Account status messages
    ACCOUNT_INACTIVE = _("This account is inactive.")
    ACCOUNT_SUSPENDED = _("This account has been suspended.")
    ACCOUNT_BLOCKED = _("This account has been blocked.")
    
    # Success messages
    LOGIN_SUCCESS = _("Welcome back!")
    LOGOUT_SUCCESS = _("You have been logged out successfully.")
    PASSWORD_CHANGED = _("Your password has been changed successfully.")
    
    # Study related messages
    INVALID_STUDY = _("Invalid study selection.")
    NO_STUDY_ACCESS = _("You don't have access to this study.")
    STUDY_SELECTED = _("Study selected successfully.")
    STUDY_CLEARED = _("Study selection cleared.")
    
    # Password reset messages
    PASSWORD_RESET_SENT = _("Password reset link has been sent to your email.")
    PASSWORD_RESET_INVALID = _("Invalid or expired reset link.")
    EMAIL_NOT_FOUND = _("No account found with this email address.")


class SessionKeys:
    """Session key constants"""
    LAST_FAILED_USERNAME = 'last_failed_username'
    CURRENT_STUDY = 'current_study'
    CURRENT_STUDY_CODE = 'current_study_code'
    CURRENT_STUDY_DB = 'current_study_db'
    CURRENT_SITE = 'current_site'
    MUST_CHANGE_PASSWORD = 'must_change_password'


class CacheKeys:
    """
    Cache key prefixes for user-related data.
    
    ✅ REFACTORED: Centralized all cache keys
    ✅ ADDED: user_blocked_{username} key for BlockedUserBackend
    """
    # Primary cache keys (used by LoginService)
    USERNAME_LOOKUP = 'username_lookup_{}'
    ACCOUNT_STATUS = 'account_status_{}'
    USER_STUDIES = 'user_studies_{}_{}'
    
    # Additional cache keys (used by various components)
    USER_BASE = 'user_{}'
    USER_BLOCKED = 'user_blocked_{}'  # ✅ ADDED: Used by BlockedUserBackend
    USER_OBJ = 'user_obj_{}'
    USER_LOGIN = 'user_login_{}'
    
    @staticmethod
    def get_username_lookup(username: str) -> str:
        """Cache key for username/email lookup"""
        return CacheKeys.USERNAME_LOOKUP.format(username)
    
    @staticmethod
    def get_account_status(username: str) -> str:
        """Cache key for account status"""
        return CacheKeys.ACCOUNT_STATUS.format(username)
    
    @staticmethod
    def get_user_studies(user_id: int, query: str = '') -> str:
        """Cache key for user's study list"""
        return CacheKeys.USER_STUDIES.format(user_id, query)
    
    @staticmethod
    def get_all_keys(username: str) -> list:
        """
        Get all possible cache keys for a username.
        
        ✅ ADDED: Helper method for bulk deletion
        
        Used by LoginService.clear_user_cache() to ensure
        all cache keys are cleared consistently.
        
        Args:
            username: Username to generate keys for
            
        Returns:
            List of all cache key strings
        """
        return [
            CacheKeys.USERNAME_LOOKUP.format(username),
            CacheKeys.ACCOUNT_STATUS.format(username),
            CacheKeys.USER_BASE.format(username),
            CacheKeys.USER_BLOCKED.format(username),
            CacheKeys.USER_OBJ.format(username),
            CacheKeys.USER_LOGIN.format(username),
        ]


class AppConstants:
    """
    Application-wide constants.
    
    ✅ ADDED: Documentation for authentication constants
    """
    DEFAULT_LANGUAGE = 'vi'
    
    # Cache timeouts
    CACHE_TIMEOUT = 300  # 5 minutes
    CACHE_TIMEOUT_SHORT = 60  # 1 minute
    CACHE_TIMEOUT_LONG = 3600  # 1 hour
    
    # Session keys for study context
    STUDY_SESSION_KEYS = [
        SessionKeys.CURRENT_STUDY,
        SessionKeys.CURRENT_STUDY_CODE,
        SessionKeys.CURRENT_STUDY_DB,
    ]
    
    # Authentication constants (for documentation)
    # Note: Actual AXES_FAILURE_LIMIT is configured in settings.py
    DEFAULT_FAILURE_LIMIT = 7
    WARNING_THRESHOLD = 2  # Show warning when <= 2 attempts remaining