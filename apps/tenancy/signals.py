# apps/tenancy/signals.py
from django.core.signals import request_finished
from django.db import connections, close_old_connections
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger('apps.tenancy')
USAGE_CACHE_KEY_PREFIX = 'study_db_usage_'

def release_unused_dbs(sender, **kwargs):
    close_old_connections()  # Django's built-in cleanup for idle connections
    # Remove inactive study DBs from connections.databases
    for db_alias in list(connections.databases.keys()):
        if db_alias != 'default' and db_alias.startswith(settings.STUDY_DB_PREFIX):
            usage_key = f"{USAGE_CACHE_KEY_PREFIX}{db_alias}"
            if not cache.get(usage_key):  # Check if recently used
                del connections.databases[db_alias]
                logger.debug(f"Released unused DB: {db_alias}")
            else:
                # Clear usage flag for next request
                cache.delete(usage_key)

request_finished.connect(release_unused_dbs)