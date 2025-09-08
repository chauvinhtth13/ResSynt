# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n"), name="set_language"),
    path("secret-admin/", admin.site.urls),
]

