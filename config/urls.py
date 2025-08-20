# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from apps.web.views import select_study, custom_login, dashboard

handler404 = 'django.views.defaults.page_not_found'  # Added: Ensures custom 404.html is used

urlpatterns = [
    path('rosetta/', include('rosetta.urls')),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        custom_login,
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path(
        "accounts/password_reset/",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="password_reset",
    ),
    path("select-study/", select_study, name="select_study"),
    path("dashboard/", dashboard, name="dashboard"),
    path("", RedirectView.as_view(pattern_name="login", permanent=False), name="home"),
]