# apps/tenancy/db_loader.py
import logging
from django.conf import settings
from django.core.cache import cache
from django.db import connections

logger = logging.getLogger('apps.tenancy')
CACHE_KEY_PREFIX = 'study_db_config_'
CACHE_TTL = 3600  # 1 hour
USAGE_CACHE_KEY_PREFIX = 'study_db_usage_'

def add_study_db(study_db_name: str) -> None:
    if study_db_name in connections.databases:
        # Mark as recently used in Redis
        cache.set(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}", True, CACHE_TTL)
        return

    cache_key = f"{CACHE_KEY_PREFIX}{study_db_name}"
    study_db_config = cache.get(cache_key)
    if not study_db_config:
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
        cache.set(cache_key, study_db_config, CACHE_TTL)
        logger.debug(f"Cached study DB config: {study_db_name}")

    connections.databases[study_db_name] = study_db_config
    # Mark as recently used in Redis
    cache.set(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}", True, CACHE_TTL)
    logger.debug(f"Added study DB config: {study_db_name}")