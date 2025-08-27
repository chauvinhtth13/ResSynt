from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Username or email"),
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "placeholder": _("Username or email"),
            "id": "username",
        }),
    )

    def clean(self):
        # Get raw input
        username_or_email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username_or_email and password:
            # Determine actual username
            actual_username = username_or_email

            # If string looks like email, try to find user by email (case-insensitive)
            if "@" in username_or_email:
                try:
                    user = User.objects.get(email__iexact=username_or_email)
                    actual_username = getattr(user, User.USERNAME_FIELD, "username")
                except User.DoesNotExist:
                    # Not found by email -> let authenticate fail normally
                    pass
                except User.MultipleObjectsReturned:
                    raise forms.ValidationError(
                        _("Multiple accounts use this email. Please use your username.")
                    )

            # Call authenticate (Django default backend needs username + password)
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