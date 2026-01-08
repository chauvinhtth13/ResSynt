# backends/api/base/account/forms.py
"""
Authentication forms with django-axes integration.
"""
import logging
from typing import Dict, Any, Optional

from django import forms
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import LoginForm

logger = logging.getLogger(__name__)


class AxesLoginForm(LoginForm):
    """
    Login form with django-axes integration.
    
    Features:
    - Honeypot field for bot detection
    - Input sanitization
    - Superuser restriction (production only)
    """
    
    # Honeypot field - bots fill this, humans won't see it
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'd-none',
            'tabindex': '-1',
            'autocomplete': 'off',
        }),
        label=''
    )
    
    def __init__(self, *args, **kwargs):
        self._lockout_info: Optional[Dict[str, Any]] = None
        super().__init__(*args, **kwargs)
        
        # Security attributes
        if 'login' in self.fields:
            self.fields['login'].widget.attrs.update({
                'autocomplete': 'username',
                'maxlength': '150',
            })
        if 'password' in self.fields:
            self.fields['password'].widget.attrs.update({
                'autocomplete': 'current-password',
                'maxlength': '128',
            })
    
    def clean_login(self) -> str:
        """Sanitize login input."""
        login = self.cleaned_data.get('login', '').strip()
        
        if len(login) > 150:
            raise forms.ValidationError(_("Input too long."))
        
        # Basic XSS prevention
        if any(c in login for c in ['<', '>', '\x00']):
            raise forms.ValidationError(_("Invalid characters."))
        
        return login
    
    def clean(self) -> Dict[str, Any]:
        """Validate with honeypot and superuser check."""
        cleaned_data = super().clean()
        
        # Honeypot check
        if cleaned_data.get('website'):
            logger.warning(f"Honeypot triggered: {cleaned_data.get('login', '')}")
            raise forms.ValidationError(_("Unable to process request."))
        
        # Block superuser - they must use /admin/login/
        self._check_superuser(cleaned_data)
        
        return cleaned_data
    
    def _check_superuser(self, cleaned_data: Dict[str, Any]) -> None:
        """Block superuser - must use /admin/login/ instead."""
        from django.contrib.auth import get_user_model
        
        login_value = cleaned_data.get('login', '')
        if not login_value:
            return
        
        User = get_user_model()
        try:
            user = User.objects.filter(
                models.Q(username__iexact=login_value) | 
                models.Q(email__iexact=login_value)
            ).first()
            
            if user and user.is_superuser:
                logger.warning(f"Superuser '{login_value}' blocked from /accounts/login/")
                raise forms.ValidationError(
                    _("Invalid credentials."),
                    code='invalid_login'
                )
        except forms.ValidationError:
            raise
        except Exception:
            pass
    
    def user_credentials(self) -> Dict[str, Any]:
        """Return credentials for auth and axes."""
        credentials = super().user_credentials()
        login_value = credentials.get('email') or credentials.get('username') or ''
        credentials['login'] = login_value
        credentials['username'] = credentials.get('username', login_value)
        return credentials
    
    def set_lockout_info(self, info: Dict[str, Any]) -> None:
        """Set lockout info for display."""
        self._lockout_info = info
    
    @property
    def is_locked_out(self) -> bool:
        """Check if locked out."""
        return bool(self._lockout_info and self._lockout_info.get('is_locked'))
    
    def add_lockout_error(self, message: str = None) -> None:
        """Add lockout error to form."""
        error_msg = message or _("Account locked. Contact administrator.")
        if not hasattr(self, '_errors') or self._errors is None:
            self._errors = forms.utils.ErrorDict()
        
        errors = self._errors.get(forms.forms.NON_FIELD_ERRORS, forms.utils.ErrorList())
        errors.append(forms.ValidationError(error_msg, code='account_locked'))
        self._errors[forms.forms.NON_FIELD_ERRORS] = errors


# Alias for backwards compatibility
LockoutAwareLoginForm = AxesLoginForm
