# apps/web/forms.py
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
        # Lấy raw input
        username_or_email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username_or_email and password:
            # Xác định username thực tế
            actual_username = username_or_email

            # Nếu chuỗi giống email, thử tìm user theo email (case-insensitive)
            if "@" in username_or_email:
                try:
                    user = User.objects.get(email__iexact=username_or_email)
                    actual_username = getattr(user, User.USERNAME_FIELD, "username")
                except User.DoesNotExist:
                    # Không tìm thấy theo email -> để authenticate fail bình thường
                    pass
                except User.MultipleObjectsReturned:
                    # Nếu hệ thống cho phép email trùng (không unique), fail rõ ràng
                    raise forms.ValidationError(
                        _("Multiple accounts use this email. Please use your username.")
                    )

            # Gọi authenticate (Django backend mặc định cần username + password)
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
