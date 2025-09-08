# backend/tenancy/signals.py - FIXED VERSION
from django.core.signals import request_finished
from django.db import connections
from django.conf import settings
from django.core.cache import cache
import logging
from typing import Set

logger = logging.getLogger('backend.tenancy')  # FIXED: Changed from 'apps.tenancy'

class DBConnectionManager:
    """Manage DB connections efficiently."""
    
    USAGE_CACHE_KEY_PREFIX = 'study_db_usage_'
    BATCH_SIZE = 10  # Process in batches
    
    @classmethod
    def release_unused_dbs(cls, sender, **kwargs):
        """Release unused study DBs."""
        # Close unusable connections first
        for conn in connections.all():
            conn.close_if_unusable_or_obsolete()
        
        # Batch process DB aliases
        study_aliases = [
            alias for alias in connections.databases.keys()
            if alias != 'default' and alias.startswith(settings.STUDY_DB_PREFIX)
        ]
        
        to_remove: Set[str] = set()
        for alias in study_aliases[:cls.BATCH_SIZE]:  # Process limited batch
            usage_key = f"{cls.USAGE_CACHE_KEY_PREFIX}{alias}"
            if not cache.get(usage_key):
                to_remove.add(alias)
            else:
                cache.delete(usage_key)  # Reset for next cycle
        
        # Batch remove
        for alias in to_remove:
            try:
                if alias in connections:
                    connections[alias].close()
                del connections.databases[alias]
                logger.debug(f"Released: {alias}")
            except Exception as e:
                logger.error(f"Error releasing {alias}: {e}")

# Connect optimized handler
request_finished.connect(DBConnectionManager.release_unused_dbs)