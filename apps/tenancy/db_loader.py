# apps/tenancy/db_loader.py
import logging
from django.db import connections
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps.tenancy")

# Cache key templates
CACHE_KEY_PREFIX = "study_db_config_"
USAGE_CACHE_KEY_PREFIX = "study_db_usage_"
CACHE_TTL = 1800  # 30 minutes for fresher configs

def add_study_db(study_db_name: str) -> None:
    """Dynamically add a study database configuration if not already present."""
    if study_db_name in connections.databases:
        # Mark as used to prevent unloading
        cache.set(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}", True, CACHE_TTL)
        return

    # Try to get config from cache
    cache_key = f"{CACHE_KEY_PREFIX}{study_db_name}"
    study_db_config = cache.get(cache_key)

    if not study_db_config:
        # Build config from settings if not cached
        study_db_config = {
            "ENGINE": settings.STUDY_DB_ENGINE,
            "NAME": study_db_name,
            "USER": settings.STUDY_DB_USER,
            "PASSWORD": settings.STUDY_DB_PASSWORD,
            "HOST": settings.STUDY_DB_HOST,
            "PORT": settings.STUDY_DB_PORT,
            "OPTIONS": {
                "options": f"-c search_path={settings.STUDY_DB_SEARCH_PATH},public",
                "sslmode": "disable" if settings.DEBUG else "require",
            },
            "CONN_MAX_AGE": settings.DATABASES["default"]["CONN_MAX_AGE"],
            "CONN_HEALTH_CHECKS": settings.DATABASES["default"]["CONN_HEALTH_CHECKS"],
            "ATOMIC_REQUESTS": settings.DATABASES["default"]["ATOMIC_REQUESTS"],
            "AUTOCOMMIT": settings.DATABASES["default"]["AUTOCOMMIT"],
            "TIME_ZONE": settings.DATABASES["default"]["TIME_ZONE"],
        }
        # Cache the config
        cache.set(cache_key, study_db_config, CACHE_TTL)
        logger.debug(f"Cached study DB config for {study_db_name}")

    # Add to connections
    connections.databases[study_db_name] = study_db_config
    # Mark as used
    cache.set(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}", True, CACHE_TTL)
    logger.debug(f"Added study DB connection for {study_db_name}")