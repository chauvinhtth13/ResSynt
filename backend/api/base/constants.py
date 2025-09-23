# backend/api/base/constants.py
from django.utils.translation import gettext_lazy as _

class LoginMessages:
    """Centralized messages for authentication system"""
    
    # Login error messages
    INVALID_CREDENTIALS = _("Invalid username or password. Please try again.")
    ACCOUNT_LOCKED = _("Account locked. Please contact support.")
    ACCOUNT_WILL_BE_LOCKED = _("Incorrect login. Account will be locked in {} attempts.")
    
    # Account status messages
    ACCOUNT_INACTIVE = _("This account is inactive.")
    ACCOUNT_SUSPENDED = _("This account has been suspended.")
    ACCOUNT_BLOCKED = _("This account has been blocked.")
    
    # Success messages
    LOGIN_SUCCESS = _("Welcome back!")
    LOGOUT_SUCCESS = _("You have been logged out successfully.")
    PASSWORD_CHANGED = _("Your password has been changed successfully.")
    
    # # Study related messages
    # INVALID_STUDY = _("Invalid study selection. Please try again.")
    # NO_STUDY_ACCESS = _("You have no access to any active studies.")
    # STUDY_SELECTED = _("Study selected successfully.")
    # STUDY_CLEARED = _("Study selection cleared.")
    
    # Password reset messages
    PASSWORD_RESET_SENT = _("Password reset link has been sent to your email.")
    PASSWORD_RESET_INVALID = _("Invalid or expired reset link.")
    EMAIL_NOT_FOUND = _("No account found with this email address.")

class SessionKeys:
    """Session key constants"""
    LAST_USERNAME = 'last_failed_username'
