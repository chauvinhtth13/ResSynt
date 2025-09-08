# apps/tenancy/db_loader.py - OPTIMIZED
import logging
from django.db import connections, connection
from django.conf import settings
from django.core.cache import cache
from typing import Optional, Dict, Any

logger = logging.getLogger("apps.tenancy")

CACHE_KEY_PREFIX = "study_db_config_"
USAGE_CACHE_KEY_PREFIX = "study_db_usage_"
CACHE_TTL = getattr(settings, 'STUDY_DB_AUTO_REFRESH_SECONDS', 300)

def get_study_db_config(study_db_name: str) -> Dict[str, Any]:
    """Build study database configuration."""
    return {
        "ENGINE": settings.STUDY_DB_ENGINE,
        "NAME": study_db_name,
        "USER": settings.STUDY_DB_USER,
        "PASSWORD": settings.STUDY_DB_PASSWORD,
        "HOST": settings.STUDY_DB_HOST,
        "PORT": settings.STUDY_DB_PORT,
        "OPTIONS": {
            "options": f"-c search_path={settings.STUDY_DB_SEARCH_PATH},public",
            "sslmode": "disable" if settings.DEBUG else "require",
            "connect_timeout": 10,
        },
        "CONN_MAX_AGE": 0 if settings.DEBUG else 600,
        "CONN_HEALTH_CHECKS": not settings.DEBUG,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "TIME_ZONE": settings.DATABASES["default"].get("TIME_ZONE", "UTC"),
    }

def add_study_db(study_db_name: str) -> None:
    """Dynamically add a study database configuration."""
    if not study_db_name.startswith(settings.STUDY_DB_PREFIX):
        logger.error(f"Invalid study DB name: {study_db_name}")
        raise ValueError(f"Study DB name must start with {settings.STUDY_DB_PREFIX}")
    
    if study_db_name in connections.databases:
        cache.set(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}", True, CACHE_TTL)
        return

    cache_key = f"{CACHE_KEY_PREFIX}{study_db_name}"
    study_db_config = cache.get(cache_key)

    if not study_db_config:
        study_db_config = get_study_db_config(study_db_name)
        cache.set(cache_key, study_db_config, CACHE_TTL)

    connections.databases[study_db_name] = study_db_config
    cache.set(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}", True, CACHE_TTL)
    logger.debug(f"Added study DB: {study_db_name}")

def remove_study_db(study_db_name: str) -> None:
    """Remove study database and close connections."""
    if study_db_name in connections:
        connections[study_db_name].close()
    if study_db_name in connections.databases:
        del connections.databases[study_db_name]
    cache.delete(f"{CACHE_KEY_PREFIX}{study_db_name}")
    cache.delete(f"{USAGE_CACHE_KEY_PREFIX}{study_db_name}")