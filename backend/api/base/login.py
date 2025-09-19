# backend/api/base/login.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Username or email"),  # English label
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "placeholder": _("Username or email"),
            "id": "username",
            "class": "form-control",
        }),
    )
    
    password = forms.CharField(
        label=_("Password"),  # English label
        widget=forms.PasswordInput(attrs={
            "placeholder": _("Password"),
            "id": "password",
            "class": "form-control",
        }),
    )
    
    error_messages = {
        'invalid_login': _(
            "Please enter a correct username and password. "
            "Note that both fields may be case-sensitive."
        ),
        'inactive': _("This account is inactive."),
    }

    def clean(self):
        username_or_email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username_or_email and password:
            # Determine actual username
            actual_username = username_or_email

            # If input looks like email, try to find user by email
            if "@" in username_or_email:
                try:
                    user = User.objects.get(email__iexact=username_or_email)
                    actual_username = getattr(user, User.USERNAME_FIELD, "username")
                except User.DoesNotExist:
                    pass
                except User.MultipleObjectsReturned:
                    raise forms.ValidationError(
                        _("Multiple accounts use this email. Please choose another email.")
                    )

            # Authenticate user
            self.user_cache = authenticate(
                self.request,
                username=actual_username,
                password=password,
            )
            
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data