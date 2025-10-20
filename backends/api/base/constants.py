# backend/api/base/constants.py
from django.utils.translation import gettext_lazy as _

class LoginMessages:
    """Centralized messages for authentication system"""
    
    # Login error messages
    INVALID_CREDENTIALS = _("Invalid login. Try again.")
    ACCOUNT_LOCKED = _("Account locked. Please contact support.")
    ACCOUNT_WILL_BE_LOCKED = _("Login failed. Lock in {} attempts.")
    
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
    """Cache key prefixes"""
    USERNAME_LOOKUP = 'username_lookup_{}'
    ACCOUNT_STATUS = 'account_status_{}'
    USER_STUDIES = 'user_studies_{}_{}'
    
    @staticmethod
    def get_username_lookup(username: str) -> str:
        return CacheKeys.USERNAME_LOOKUP.format(username)
    
    @staticmethod
    def get_account_status(username: str) -> str:
        return CacheKeys.ACCOUNT_STATUS.format(username)
    
    @staticmethod
    def get_user_studies(user_id: int, query: str = '') -> str:
        return CacheKeys.USER_STUDIES.format(user_id, query)


class AppConstants:
    """Application-wide constants"""
    DEFAULT_LANGUAGE = 'vi'
    CACHE_TIMEOUT = 300  # 5 minutes
    CACHE_TIMEOUT_SHORT = 60  # 1 minute
    STUDY_SESSION_KEYS = [
        SessionKeys.CURRENT_STUDY,
        SessionKeys.CURRENT_STUDY_CODE,
        SessionKeys.CURRENT_STUDY_DB,
    ]