# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect
from backend.web.views import custom_login, select_study, dashboard
from django.conf import settings

handler404 = 'django.views.defaults.page_not_found'

def root_redirect(request):
    """Redirect root based on auth status."""
    if request.user.is_authenticated:
        return redirect('select_study')
    return redirect('login')

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n"), name="set_language"),
    path("secret-admin/", admin.site.urls),
    
    # Authentication
    path("accounts/login/", never_cache(custom_login), name="login"),
    path("accounts/logout/", never_cache(auth_views.LogoutView.as_view(next_page="login")), name="logout"),
    
    # Study selection and dashboard
    path("select-study/", never_cache(select_study), name="select_study"),
    path("dashboard/", never_cache(dashboard), name="dashboard"),
    
    # Study-specific URLs (dynamic routing)
    path("studies/", include("apps.studies.urls")),
    
    # Root redirect
    path("", never_cache(root_redirect), name="home"),
]

# Password reset URLs (conditional)
if settings.FEATURE_PASSWORD_RESET:
    urlpatterns += [
        path("accounts/password_reset/", 
             auth_views.PasswordResetView.as_view(
                 template_name="default/reset_password_form.html",
                 email_template_name="default/reset_password_email.html",
                 subject_template_name="default/reset_password_subject.txt",
             ), name="password_reset"),
        path("accounts/password_reset/done/",
             auth_views.PasswordResetDoneView.as_view(
                 template_name="default/reset_password_done.html"
             ), name="password_reset_done"),
        path("accounts/reset/<uidb64>/<token>/",
             auth_views.PasswordResetConfirmView.as_view(
                 template_name="default/reset_password_confirm.html"
             ), name="password_reset_confirm"),
        path("accounts/reset/done/",
             auth_views.PasswordResetCompleteView.as_view(
                 template_name="default/reset_password_complete.html"
             ), name="password_reset_complete"),
    ]
else:
    urlpatterns.append(
        path("accounts/password_reset/",
             RedirectView.as_view(pattern_name="login", permanent=False),
             name="password_reset")
    )

# Serve media files in development
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)