# backends/api/base/account/forms.py
"""
Custom authentication forms with django-axes integration.
Provides enhanced security and proper credential tracking.
"""
import logging
from typing import Dict, Any, Optional

from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import LoginForm

logger = logging.getLogger(__name__)


class AxesLoginForm(LoginForm):
    """
    Extended login form for django-axes compatibility with allauth.
    
    Features:
    - Proper credential passing for axes tracking
    - Enhanced error messages for security events
    - Honeypot field for bot detection
    - Rate limit awareness
    - Lockout info handling
    
    Note: Allauth uses 'login' field, but axes expects credentials dict
    with consistent keys. This form ensures compatibility.
    """
    
    # Honeypot field - bots will fill this, humans won't see it
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'd-none',  # Hidden via CSS
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        }),
        label=''
    )
    
    def __init__(self, *args, **kwargs):
        # Initialize lockout info before super() - DON'T extract request from kwargs
        # allauth's LoginForm needs request in kwargs
        self._lockout_info: Optional[Dict[str, Any]] = None
        super().__init__(*args, **kwargs)
        # Add security attributes to login field
        if 'login' in self.fields:
            self.fields['login'].widget.attrs.update({
                'autocomplete': 'username',
                'autocapitalize': 'none',
                'spellcheck': 'false',
            })
        if 'password' in self.fields:
            self.fields['password'].widget.attrs.update({
                'autocomplete': 'current-password',
            })
    
    def clean(self) -> Dict[str, Any]:
        """
        Validate form with honeypot check and superuser restriction.
        """
        cleaned_data = super().clean()
        
        # Honeypot check - if filled, likely a bot
        if cleaned_data.get('website'):
            logger.warning(
                f"Honeypot triggered for login attempt: {cleaned_data.get('login', 'unknown')}"
            )
            # Don't reveal honeypot detection - just show generic error
            raise forms.ValidationError(
                _("Unable to process your request. Please try again."),
                code='honeypot_triggered'
            )
        
        # Block superuser from logging in via normal login page
        # Superusers must use /admin/ login
        self._check_superuser_restriction(cleaned_data)
        
        return cleaned_data
    
    def _check_superuser_restriction(self, cleaned_data: Dict[str, Any]) -> None:
        """
        Prevent superuser from logging in via normal login page.
        
        SECURITY: Superusers should only login via Django admin.
        This prevents admin credentials from being used on the main site.
        """
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        login_value = cleaned_data.get('login', '')
        
        if not login_value:
            return
        
        try:
            # Try to find user by username or email
            user = User.objects.filter(
                models.Q(username__iexact=login_value) | 
                models.Q(email__iexact=login_value)
            ).first()
            
            if user and user.is_superuser:
                logger.warning(
                    f"Superuser '{login_value}' attempted login via normal login page - blocked"
                )
                # Show generic error - don't reveal that user exists
                raise forms.ValidationError(
                    _("The username and/or password you specified are not correct."),
                    code='invalid_login'
                )
        except Exception as e:
            # Don't break login if check fails
            logger.debug(f"Superuser check failed: {e}")
    
    def user_credentials(self) -> Dict[str, Any]:
        """
        Return user credentials for authentication.
        
        IMPORTANT: This method is called by allauth and axes.
        We ensure both 'login' and 'username' keys exist for compatibility.
        
        Returns:
            Dict with credentials including 'login', 'username', and 'password'
        """
        credentials = super().user_credentials()
        
        # Get the login value (could be username or email)
        login_value = credentials.get('email') or credentials.get('username') or ''
        
        # Ensure 'login' key exists for axes (AXES_USERNAME_FORM_FIELD = 'login')
        credentials['login'] = login_value
        
        # Also ensure 'username' exists as fallback
        if 'username' not in credentials:
            credentials['username'] = login_value
        
        return credentials
    
    def get_credentials_for_axes(self) -> Dict[str, str]:
        """
        Get credentials specifically formatted for axes tracking.
        
        Returns:
            Dict with 'username' and 'login' keys
        """
        login_value = self.cleaned_data.get('login', '')
        return {
            'username': login_value,
            'login': login_value,
        }
    
    def set_lockout_info(self, info: Dict[str, Any]) -> None:
        """Set lockout information for display."""
        self._lockout_info = info
    
    @property
    def is_locked_out(self) -> bool:
        """Check if the form is in lockout state."""
        return self._lockout_info is not None and self._lockout_info.get('is_locked', False)
    
    @property
    def lockout_message(self) -> str:
        """Get the lockout message."""
        if self._lockout_info:
            return self._lockout_info.get('message', '')
        return ''
    
    def add_lockout_error(self, message: str = None) -> None:
        """Add lockout error to form without requiring validation."""
        error_message = message or _(
            "Your account has been locked. Please contact administrator for assistance."
        )
        # Initialize errors dict if not exists (form not validated yet)
        if not hasattr(self, '_errors') or self._errors is None:
            self._errors = forms.utils.ErrorDict()
        
        # Add non-field error directly without requiring cleaned_data
        non_field_errors = self._errors.get(forms.forms.NON_FIELD_ERRORS, forms.utils.ErrorList())
        non_field_errors.append(forms.ValidationError(error_message, code='account_locked'))
        self._errors[forms.forms.NON_FIELD_ERRORS] = non_field_errors


class LockoutAwareLoginForm(AxesLoginForm):
    """
    Login form that's aware of lockout status.
    Can display remaining attempts or lockout message.
    
    Note: This class is kept for backwards compatibility but
    AxesLoginForm now has all the same lockout-aware features.
    """
    pass  # All functionality is now in AxesLoginForm
