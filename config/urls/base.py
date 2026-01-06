"""
Base URL patterns - Core Django and authentication routes.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from backends.api.base.account.views import SecureLoginView
from backends.api.base.account.forms import AxesLoginForm


# Core URL patterns (always available)
urlpatterns = [
    # Internationalization
    path("i18n/", include("django.conf.urls.i18n")),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # Home redirect to login
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False), name='home'),
    
    # Custom secure login (must be BEFORE allauth.urls to override)
    path(
        "accounts/login/",
        SecureLoginView.as_view(form_class=AxesLoginForm),
        name="account_login"
    ),
    
    # Authentication (allauth - other routes)
    path("accounts/", include("allauth.urls")),

    # Base API (tenancy, common endpoints)
    path('', include('backends.api.base.urls')),
]
    