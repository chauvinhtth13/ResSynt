# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.web.login import UsernameOrEmailAuthenticationForm

urlpatterns = [
    
     # i18n (đổi ngôn ngữ)
    path("i18n/", include("django.conf.urls.i18n")),

    # Django Admin
    path("admin/", admin.site.urls),

    # Auth
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="default/login.html",
            authentication_form=UsernameOrEmailAuthenticationForm
        ),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    
    path(
        "accounts/password_reset/",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="password_reset",
    ),

    # path("accounts/password_reset/",
    #  auth_views.PasswordResetView.as_view(
    #      template_name="default/reset_password_form.html",
    #      email_template_name="default/reset_password_email.html",
    #      subject_template_name="default/reset_password_subject.txt",
    #  ),
    #  name="password_reset"),
    
    # path("accounts/password_reset/done/",
    #     auth_views.PasswordResetDoneView.as_view(
    #         template_name="default/reset_password_done.html"
    #     ),
    #     name="password_reset_done"),
    
    # path("accounts/reset/<uidb64>/<token>/",
    #     auth_views.PasswordResetConfirmView.as_view(
    #         template_name="default/reset_password_confirm.html"
    #     ),
    #     name="password_reset_confirm"),
    
    # path("accounts/reset/done/",
    #     auth_views.PasswordResetCompleteView.as_view(
    #         template_name="default/reset_password_complete.html"
    #     ),
    #     name="password_reset_complete"),

    # Trang chủ (tạm chuyển hướng về login nếu chưa có app web)
    #path("", RedirectView.as_view(pattern_name="login", permanent=False), name="home"),
    
    # (Khi sẵn sàng) bật routes của app web:
    #path("", include("apps.web.urls"))
]

# Dev: serve static & media an toàn
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if hasattr(settings, "MEDIA_URL") and hasattr(settings, "MEDIA_ROOT"):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path(
            "favicon.ico",
            RedirectView.as_view(
                url=f"{settings.STATIC_URL}images/default/favicon.ico",
                permanent=False
            ),
        ),
    ]
