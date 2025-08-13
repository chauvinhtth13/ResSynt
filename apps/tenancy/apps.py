# apps/tenancy/apps.py
# This defines TenancyConfig to handle app initialization, including loading active study DBs if needed.
# Assumptions:
# - On startup, pre-load all active study DBs into DATABASES for better performance.
# - Use a simple cache or periodic refresh (not implemented here; could use django-cache or APScheduler).
# - For STUDY_DB_AUTO_REFRESH_SECONDS, you can add a background thread in ready() to refresh periodically.
# - Import models only in ready() to avoid import issues.

from django.apps import AppConfig
from django.conf import settings
import threading
import time

class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenancy'

    def ready(self):
        if not settings.TENANCY_ENABLED:
            return

        # Pre-load active studies on startup
        self.load_study_dbs()

        # Optional: Start a background thread for periodic refresh
        if settings.STUDY_DB_AUTO_REFRESH_SECONDS > 0:
            def refresh_loop():
                while True:
                    time.sleep(settings.STUDY_DB_AUTO_REFRESH_SECONDS)
                    self.load_study_dbs()

            threading.Thread(target=refresh_loop, daemon=True).start()

    def load_study_dbs(self):
        from .models import Study  # Lazy import

        for study in Study.objects.filter(status='active'):
            db_alias = study.db_name
            if db_alias not in settings.DATABASES:
                settings.DATABASES[db_alias] = {
                    'ENGINE': settings.STUDY_DB_ENGINE,
                    'NAME': db_alias,
                    'USER': settings.STUDY_DB_USER,
                    'PASSWORD': settings.STUDY_DB_PASSWORD,
                    'HOST': settings.STUDY_DB_HOST,
                    'PORT': settings.STUDY_DB_PORT,
                    'OPTIONS': {'options': f"-c search_path={settings.STUDY_DB_SEARCH_PATH}"},
                    'TIME_ZONE': settings._DB_MANAGEMENT.get('TIME_ZONE'),
                    'ATOMIC_REQUESTS': settings._DB_MANAGEMENT.get('ATOMIC_REQUESTS', False),
                    'AUTOCOMMIT': settings._DB_MANAGEMENT.get('AUTOCOMMIT', True),
                    'CONN_MAX_AGE': settings._DB_MANAGEMENT.get('CONN_MAX_AGE', 600),
                    'CONN_HEALTH_CHECKS': settings._DB_MANAGEMENT.get('CONN_HEALTH_CHECKS', False),
                }