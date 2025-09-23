# backend/tenancy/apps.py
from django.apps import AppConfig

class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.tenancy'  # FIXED: Changed from 'apps.tenancy' to 'backend.tenancy'
    verbose_name = "Tenancy Management"

    def ready(self):
        import backend.tenancy.signals  # FIXED: Updated import path