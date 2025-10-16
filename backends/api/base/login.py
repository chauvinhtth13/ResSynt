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
    
    # Alternative fix if the above doesn't work:
    # def get_user(self):  # type: ignore[override]
    #     """Return the authenticated user"""
    #     return self.user_cache


# class PasswordResetRequestForm(forms.Form):
#     """
#     Form for requesting password reset via email.
#     Bonus form for future implementation.
#     """
#     email = forms.EmailField(
#         label=_("Email Address"),
#         max_length=254,
#         required=True,
#         widget=forms.EmailInput(attrs={
#             'placeholder': _('Enter your email address'),
#             'autocomplete': 'email',
#         })
#     )
    
#     def clean_email(self) -> str:
#         """Validate and normalize email"""
#         email = self.cleaned_data.get('email', '').strip().lower()
        
#         if not email:
#             raise ValidationError(_("Please enter your email address."))
        
#         # Check if email exists
#         if not User.objects.filter(email__iexact=email, is_active=True).exists():
#             raise ValidationError(
#                 _("No active account found with this email address."),
#                 code='email_not_found',
#             )
        
#         return email
    
#     def save(self, request=None) -> None:
#         """
#         Generate and send password reset email.
#         To be implemented with Django's password reset views.
#         """
#         email = self.cleaned_data['email']
#         # Implementation would go here
#         # This is just a placeholder for future use
#         pass


# class ChangePasswordForm(forms.Form):
#     """
#     Form for changing password (for users marked with must_change_password).
#     Bonus form for future implementation.
#     """
#     old_password = forms.CharField(
#         label=_("Current Password"),
#         strip=False,
#         widget=forms.PasswordInput,
#     )
    
#     new_password1 = forms.CharField(
#         label=_("New Password"),
#         strip=False,
#         widget=forms.PasswordInput,
#         help_text=_("Password must be at least 8 characters long."),
#     )
    
#     new_password2 = forms.CharField(
#         label=_("Confirm New Password"),
#         strip=False,
#         widget=forms.PasswordInput,
#     )
    
#     def __init__(self, user: AbstractBaseUser, *args, **kwargs):
#         self.user = user
#         super().__init__(*args, **kwargs)
    
#     def clean_old_password(self) -> str:
#         """Validate current password"""
#         old_password = self.cleaned_data.get('old_password')
        
#         if not self.user.check_password(old_password):
#             raise ValidationError(
#                 _("Your current password was entered incorrectly."),
#                 code='password_incorrect',
#             )
        
#         return old_password
    
#     def clean(self) -> dict:
#         """Validate new passwords match and meet requirements"""
#         cleaned_data = super().clean()
#         password1 = cleaned_data.get('new_password1')
#         password2 = cleaned_data.get('new_password2')
        
#         if password1 and password2:
#             if password1 != password2:
#                 raise ValidationError(
#                     _("The two password fields didn't match."),
#                     code='password_mismatch',
#                 )
            
#             # Minimum length check
#             if len(password1) < 8:
#                 raise ValidationError(
#                     _("Password must be at least 8 characters long."),
#                     code='password_too_short',
#                 )
        
#         return cleaned_data
    
#     def save(self, commit: bool = True) -> AbstractBaseUser:
#         """Save the new password"""
#         password = self.cleaned_data['new_password1']
#         self.user.set_password(password)
        
#         # Clear must_change_password flag
#         if hasattr(self.user, 'must_change_password'):
#             self.user.must_change_password = False
        
#         # Update password_changed_at timestamp
#         if hasattr(self.user, 'password_changed_at'):
#             from django.utils import timezone
#             self.user.password_changed_at = timezone.now()
        
#         if commit:
#             self.user.save()
        
#         return self.user