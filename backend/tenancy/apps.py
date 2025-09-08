# backend/tenancy/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.tenancy'  # FIXED: Changed from 'apps.tenancy' to 'backend.tenancy'
    verbose_name = _("Tenancy Management")

    def ready(self):
        import backend.tenancy.signals  # FIXED: Updated import path