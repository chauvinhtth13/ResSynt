# apps/tenancy/db_loader.py
# This module handles dynamic loading of per-study databases into settings.DATABASES.
# Optimizations:
# - Use cache (Django's default cache, e.g., Redis or LocMem) to store DB configs for STUDY_DB_AUTO_REFRESH_SECONDS seconds.
# - Only load active studies (status='active' from models.py).
# - Deepcopy default DB config and override NAME and OPTIONS (search_path to 'data').
# - Conditional SSL based on DEBUG (disable in dev, require in prod).
# - Force_refresh param for commands (e.g., create_study) to update immediately.
# - Logging for errors/debugging.
# - Aligned with models.py: Use Study model with status filter.
# - Call this in middleware (on each request, but cached) or in AppConfig ready() for initial load.

import copy
import logging
from django.conf import settings
from django.core.cache import cache
from .models import Study

logger = logging.getLogger('apps.tenancy')

def load_study_dbs(force_refresh=False):
    """
    Load and cache dynamic DB configs for active studies.
    Returns the updated DATABASES dict.
    """
    cache_key = 'study_dbs_config'
    study_dbs = cache.get(cache_key)
    if study_dbs is None or force_refresh:
        study_dbs = {}
        try:
            active_studies = Study.objects.filter(status=Study.Status.ACTIVE)
            
            # Remove stale study DBs from settings.DATABASES
            for db_alias in list(settings.DATABASES.keys()):
                if db_alias != 'default' and db_alias.startswith(settings.STUDY_DB_PREFIX):
                    del settings.DATABASES[db_alias]
                    logger.debug(f"Removed stale DB config: {db_alias}")
            
            for study in active_studies:
                db_alias = study.db_name
                db_config = copy.deepcopy(settings.DATABASES['default'])
                db_config.update({
                    'NAME': study.db_name,
                    'OPTIONS': {
                        'options': f"-c search_path={settings.STUDY_DB_SEARCH_PATH}",
                        'sslmode': 'disable' if settings.DEBUG else 'require',
                    },
                })
                study_dbs[db_alias] = db_config
                logger.debug(f"Added DB config for study {study.code}: {db_alias}")
            
            cache.set(cache_key, study_dbs, settings.STUDY_DB_AUTO_REFRESH_SECONDS)
            settings.DATABASES.update(study_dbs)
        except Exception as e:
            logger.error(f"Error loading study DBs: {e}")
    else:
        # If cached, ensure they're in DATABASES (in case of restart)
        settings.DATABASES.update(study_dbs)
    return settings.DATABASES