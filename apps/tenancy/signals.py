# apps/tenancy/signals.py
from django.core.signals import request_finished
from django.db import connections
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger('apps.tenancy')
USAGE_CACHE_KEY_PREFIX = 'study_db_usage_'

def release_unused_dbs(sender, **kwargs):
    # Close old connections first
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()

    # Remove inactive study DBs from connections.databases
    for db_alias in list(connections.databases.keys()):
        if db_alias != 'default' and db_alias.startswith(settings.STUDY_DB_PREFIX):
            usage_key = f"{USAGE_CACHE_KEY_PREFIX}{db_alias}"
            if not cache.get(usage_key):
                if db_alias in connections.databases:
                    del connections.databases[db_alias]
                    logger.debug(f"Released unused DB: {db_alias}")
            else:
                # Reset usage flag after check to allow unloading if not used in next cycle
                cache.delete(usage_key)

request_finished.connect(release_unused_dbs)