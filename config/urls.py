# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from apps.web.login import UsernameOrEmailAuthenticationForm
from apps.web.views import select_study # Import the new view

urlpatterns = [
    # i18n (language switch)
    path('rosetta/', include('rosetta.urls')),

    path("i18n/", include("django.conf.urls.i18n")),

    # Django Admin (changed default path for security)
    path("admin/", admin.site.urls),

    # Auth (changed prefix 'accounts/' to 'secure-auth/' for security)
    path(
        "secure-auth/login/",
        auth_views.LoginView.as_view(
            template_name="default/login.html",
            authentication_form=UsernameOrEmailAuthenticationForm,
        ),
        name="login",
    ),
    path(
        "secure-auth/logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    
    # Redirect password reset to login to disable and hide the feature if not used
    path(
        "secure-auth/password_reset/",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="password_reset",
    ),

    # Select study page
    path("select-study/", select_study, name="select_study"),

    # Home (redirect to login)
    path("", RedirectView.as_view(pattern_name="login", permanent=False), name="home"),
]