# apps/tenancy/apps.py
from django.apps import AppConfig

class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenancy'
    verbose_name = "Tenancy Management"

    def ready(self):
        # Removed load_study_dbs() to avoid DB access during app init.
        # Loading will happen lazily in middleware on first request.
        pass