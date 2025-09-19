# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from backend.api.base import views as base_views


urlpatterns = [
    # Admin site
    path("i18n/", include("django.conf.urls.i18n"), name="set_language"),
    path("secret-admin/", admin.site.urls),

    # Authentication - FIX: Add name="login"
    path("", never_cache(base_views.custom_login), name=""),
    path("logout/", never_cache(base_views.logout_view), name="logout"),

    # Base app
    path("select-study/", base_views.select_study, name="select_study"),
    path("dashboard/", base_views.dashboard, name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)