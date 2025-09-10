# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect
from django.conf import settings
from backend.api.base import views as base_views

def root_redirect(request):
    """Redirect root based on auth status."""
    if request.user.is_authenticated:
        return redirect('select_study')
    return redirect('login')


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n"), name="set_language"),
    path("secret-admin/", admin.site.urls),
    path("accounts/login/", never_cache(base_views.custom_login), name="login"),
    path("accounts/logout/", never_cache(auth_views.LogoutView.as_view(next_page="login")), name="logout"),
    path("select-study/", base_views.select_study, name="select_study"),
    path("dashboard/", base_views.dashboard, name="dashboard"),
    path("", base_views.custom_login, name="login"),
]

