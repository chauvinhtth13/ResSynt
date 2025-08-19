# apps/tenancy/db_loader.py
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
            active_studies = Study.objects.filter(status=Study.Status.ACTIVE).values('code', 'db_name')
            active_db_names = {study['db_name'] for study in active_studies}
            
            # Remove stale study DBs from settings.DATABASES
            for db_alias in list(settings.DATABASES.keys()):
                if db_alias.startswith(settings.STUDY_DB_PREFIX) and db_alias not in active_db_names:
                    del settings.DATABASES[db_alias]
                    logger.debug(f"Removed stale DB config: {db_alias}")
            
            for study in active_studies:
                db_alias = study['db_name']
                db_config = copy.deepcopy(settings.DATABASES['default'])
                db_config.update({
                    'NAME': db_alias,
                    'OPTIONS': {
                        'options': f"-c search_path={settings.STUDY_DB_SEARCH_PATH}",
                        'sslmode': 'disable' if settings.DEBUG else 'require',
                    },
                })
                study_dbs[db_alias] = db_config
                settings.DATABASES[db_alias] = db_config  # Update immediately
                logger.debug(f"Added DB config for study {study['code']}: {db_alias}")
            
            cache.set(cache_key, study_dbs, settings.STUDY_DB_AUTO_REFRESH_SECONDS)
        except Exception as e:
            logger.error(f"Error loading study DBs: {e}")
            if settings.DEBUG:
                raise  # Raise in debug for development
    else:
        # If cached, ensure they're in DATABASES (e.g., after process restart)
        for db_alias, db_config in study_dbs.items():
            if db_alias not in settings.DATABASES:
                settings.DATABASES[db_alias] = db_config
                logger.debug(f"Restored DB config from cache: {db_alias}")
    
    return settings.DATABASES