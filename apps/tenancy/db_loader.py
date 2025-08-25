# apps/tenancy/db_loader.py
import logging
from django.conf import settings
from django.db import connections

logger = logging.getLogger('apps.tenancy')

def add_study_db(study_db_name: str) -> None:
    if study_db_name in connections.databases:
        return

    study_db_config = {
        'ENGINE': settings.STUDY_DB_ENGINE,
        'NAME': study_db_name,
        'USER': settings.STUDY_DB_USER,
        'PASSWORD': settings.STUDY_DB_PASSWORD,
        'HOST': settings.STUDY_DB_HOST,
        'PORT': settings.STUDY_DB_PORT,
        'OPTIONS': {
            'options': f"-c search_path={settings.STUDY_DB_SEARCH_PATH},public",
            'sslmode': 'disable' if settings.DEBUG else 'require',
        },
        'CONN_MAX_AGE': settings.DATABASES['default']['CONN_MAX_AGE'],
        'CONN_HEALTH_CHECKS': settings.DATABASES['default']['CONN_HEALTH_CHECKS'],
        'ATOMIC_REQUESTS': settings.DATABASES['default']['ATOMIC_REQUESTS'],
        'AUTOCOMMIT': settings.DATABASES['default']['AUTOCOMMIT'],
        'TIME_ZONE': settings.DATABASES['default']['TIME_ZONE'],
    }
    connections.databases[study_db_name] = study_db_config
    logger.debug(f"Added study DB config: {study_db_name}")