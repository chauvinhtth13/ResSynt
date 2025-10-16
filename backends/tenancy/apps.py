# backend/tenancy/apps.py
from django.apps import AppConfig

class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.tenancy'  # FIXED: Changed from 'apps.tenancy' to 'backends.tenancy'
    verbose_name = "Tenancy Management"

    def ready(self):
        import backends.tenancy.signals  # FIXED: Updated import path