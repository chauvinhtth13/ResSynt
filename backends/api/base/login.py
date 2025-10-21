# backend/api/base/login.py
from typing import Optional, Any
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form that accepts username or email.
    Minimal approach - let template handle styling with Bootstrap.
    """
    
    # Simple fields without custom widgets - Bootstrap styling in template
    username = forms.CharField(
        label=_("Username or email"),
        max_length=254,
        required=True,
    )
    
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        required=True,
    )
    
    # Minimal error messages - specific messages handled in views
    error_messages = {
        'invalid_login': ' ',  # Single space to avoid empty validation
        'inactive': _('This account is inactive.'),
        'suspended': _('This account has been suspended.'),
        'blocked': _('This account has been blocked.'),
    }
    
    def __init__(self, request=None, *args, **kwargs):
        """Initialize with request context"""
        super().__init__(request, *args, **kwargs)
        self.user_cache: Optional[AbstractBaseUser] = None
    
    def clean_username(self):
        """Clean and normalize username/email input"""
        username = self.cleaned_data.get('username', '')
        # Strip whitespace and convert to lowercase for email
        username = username.strip()
        if '@' in username:
            username = username.lower()
        return username
    
    def clean_password(self):
        """Clean password - just strip trailing spaces"""
        password = self.cleaned_data.get('password', '')
        return password.rstrip()
    
    def clean(self):
        """
        Authenticate user without revealing whether username exists.
        Let views.py handle specific error messages.
        """
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if not username_or_email or not password:
            # If fields are empty, let field validation handle it
            return self.cleaned_data
        
        # Find actual username
        actual_username = self._get_actual_username(username_or_email)
        
        if actual_username:
            # Try authentication
            self.user_cache = authenticate(
                self.request,
                username=actual_username,
                password=password
            )
            
            if self.user_cache is None:
                # Authentication failed - don't specify why
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            else:
                # Check if user is allowed to login
                self.confirm_login_allowed(self.user_cache)
        else:
            # User not found - still raise generic error
            raise ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
            )
        
        return self.cleaned_data
    
    def _get_actual_username(self, username_or_email: str) -> Optional[str]:
        """
        Convert email to username if needed.
        Returns None if user doesn't exist.
        """
        try:
            if '@' in username_or_email:
                # Input is email - find user by email
                user = User.objects.only('username').get(
                    email__iexact=username_or_email
                )
                return user.username
            else:
                # Input is username - verify it exists
                if User.objects.filter(username__iexact=username_or_email).exists():
                    return username_or_email
                return None
                
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Multiple users with same email - security issue
            logger.error(f"Multiple users found with email: {username_or_email}")
            # Don't reveal this to user - return None
            return None
    
    def confirm_login_allowed(self, user: AbstractBaseUser) -> None:
        """
        Additional checks for user login eligibility.
        Called after successful authentication.
        """
        # Check Django's is_active flag
        if not user.is_active:
            raise ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )
        
        # Check custom status field if exists
        if hasattr(user, 'status'):
            # Import here to avoid circular dependency
            from backends.tenancy.models.user import User as CustomUser
            
            # Map status to error messages
            status_errors = {
                CustomUser.Status.INACTIVE: 'inactive',
                CustomUser.Status.SUSPENDED: 'suspended',
                CustomUser.Status.BLOCKED: 'blocked',
            }
            
            user_status = getattr(user, 'status')
            if user_status in status_errors:
                error_code = status_errors[user_status]
                raise ValidationError(
                    self.error_messages[error_code],
                    code=error_code,
                )
        
        # Check if user must change password (optional)
        if hasattr(user, 'must_change_password') and getattr(user, 'must_change_password', False):
            # Store flag in session to redirect after login
            if self.request:
                self.request.session['must_change_password'] = True
    
    def get_user(self) -> Any:  # Using Any to match Django's signature
        """Return the authenticated user"""
        return self.user_cache