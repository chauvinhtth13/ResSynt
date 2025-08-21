# apps/tenancy/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenancy'
    verbose_name = _("Tenancy Management")

    def ready(self):
        from .db_loader import load_study_dbs
        load_study_dbs(force_refresh=True)  # Preload active study DBs on app startup for performance