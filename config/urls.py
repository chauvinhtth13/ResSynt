# config/urls.py (change admin path to obscure it)
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache
from apps.web.views import select_study, custom_login, dashboard
from config import settings

handler404 = 'django.views.defaults.page_not_found'  # Ensures custom 404.html is used

urlpatterns = [
    path('rosetta/', include('rosetta.urls')),
    path("i18n/", include("django.conf.urls.i18n")),
    path("secret-admin/", admin.site.urls),  # Changed from "admin/" for security
    path(
        "accounts/login/",
        never_cache(custom_login),
        name="login",
    ),
    path(
        "accounts/logout/",
        never_cache(auth_views.LogoutView.as_view(next_page="login")),  # Wrap with never_cache
        name="logout",
    ),
    path("select-study/", never_cache(select_study), name="select_study"),
    path("dashboard/", never_cache(dashboard), name="dashboard"),
    path("", RedirectView.as_view(pattern_name="login", permanent=False), name="home"),
]

if settings.FEATURE_PASSWORD_RESET:
    urlpatterns += [
        path(
            "accounts/password_reset/",
            auth_views.PasswordResetView.as_view(
                template_name="default/reset_password_form.html",
                email_template_name="default/reset_password_email.html",
                subject_template_name="default/reset_password_subject.txt",
            ),
            name="password_reset",
        ),
        path(
            "accounts/password_reset/done/",
            auth_views.PasswordResetDoneView.as_view(template_name="default/reset_password_done.html"),
            name="password_reset_done",
        ),
        path(
            "accounts/reset/<uidb64>/<token>/",
            auth_views.PasswordResetConfirmView.as_view(template_name="default/reset_password_confirm.html"),
            name="password_reset_confirm",
        ),
        path(
            "accounts/reset/done/",
            auth_views.PasswordResetCompleteView.as_view(template_name="default/reset_password_complete.html"),
            name="password_reset_complete",
        ),
    ]
else:
    urlpatterns += [
        path(
            "accounts/password_reset/",
            RedirectView.as_view(pattern_name="login", permanent=False),
            name="password_reset",
        ),
    ]