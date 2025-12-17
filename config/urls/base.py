"""
Base URL patterns - Core Django and authentication routes.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView


# Core URL patterns (always available)
urlpatterns = [
    # Internationalization
    path("i18n/", include("django.conf.urls.i18n")),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # Authentication (allauth)
    path("accounts/", include("allauth.urls")),
    
    # Home redirect to login
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False), name='home'),
    
    # Base API (tenancy, common endpoints)
    path('', include('backends.api.base.urls')),
]

# Django Debug Toolbar (development only)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass