# backends/tenancy/db_router.py - PRODUCTION-READY VERSION
import logging
import threading
from typing import Any, Dict, Optional, Set

from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Thread-Local Database Context
# =============================================================================

_thread_local = threading.local()


def get_current_db() -> str:
    """Get current database for this thread."""
    return getattr(_thread_local, 'db', 'default')


def set_current_db(db_alias: str) -> None:
    """Set current database for this thread."""
    _thread_local.db = db_alias if db_alias else 'default'


def clear_current_db() -> None:
    """Clear current database context."""
    if hasattr(_thread_local, 'db'):
        del _thread_local.db


# =============================================================================
# Database Router
# =============================================================================

class TenantRouter:
    """
    Multi-tenant database router with intelligent routing.
    
    Features:
    - App-based routing to management or study databases
    - Thread-safe caching with minimal lock contention
    - Migration control per database type
    """
    
    # Apps that MUST use management database
    MANAGEMENT_APPS: frozenset = frozenset({
        'admin',
        'auth',
        'contenttypes',
        'sessions',
        'messages',
        'staticfiles',
        'tenancy',
        'axes',
        'usersessions',
        'sites',
        'account',  # allauth
    })
    
    # Apps that use study databases
    STUDY_APPS: frozenset = frozenset({
        'studies',
        # Note: audit_logs models are now created per-study via factory
        # with app_label = 'study_XXen', so they route automatically
    })
    
    # Class-level cache (shared across instances)
    _routing_cache: Dict[str, str] = {}
    _migration_cache: Dict[tuple, bool] = {}
    _cache_lock = threading.Lock()
    
    # =========================================================================
    # Core Routing Methods
    # =========================================================================
    
    def db_for_read(self, model, **hints) -> str:
        """Route read operations."""
        return self._get_db_for_model(model)
    
    def db_for_write(self, model, **hints) -> str:
        """Route write operations."""
        return self._get_db_for_model(model)
    
    def _get_db_for_model(self, model) -> str:
        """
        Determine database for a model.
        
        Uses lock-free read with locked write pattern for better performance.
        """
        app_label = model._meta.app_label
        
        # Fast path: check cache without lock
        cached = self._routing_cache.get(app_label)
        if cached is not None:
            # For study apps, always use thread context
            if cached == '_STUDY_':
                return get_current_db()
            return cached
        
        # Determine database
        if app_label in self.MANAGEMENT_APPS:
            db = 'default'
        elif app_label in self.STUDY_APPS or app_label.startswith('study_'):
            db = '_STUDY_'  # Marker for study apps
        else:
            db = '_STUDY_'  # Unknown apps follow thread context
        
        # Cache result (lock only on write)
        with self._cache_lock:
            self._routing_cache[app_label] = db
        
        return get_current_db() if db == '_STUDY_' else db
    
    # =========================================================================
    # Relation Control
    # =========================================================================
    
    def allow_relation(self, obj1, obj2, **hints) -> Optional[bool]:
        """
        Allow relations only within same database.
        """
        db1 = self._get_db_for_model(obj1.__class__)
        db2 = self._get_db_for_model(obj2.__class__)
        
        if db1 == db2:
            return True
        
        # Cross-database relations not allowed
        return False
    
    # =========================================================================
    # Migration Control
    # =========================================================================
    
    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints) -> bool:
        """
        Control migration routing.
        
        Rules:
        - Management apps: only on 'default'
        - Study apps: only on study databases (db_study_*)
        - Unknown apps: follow standard rules
        """
        # Check cache without lock (fast path)
        cache_key = (db, app_label)
        cached = self._migration_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Compute result
        result = self._compute_migration_allowed(db, app_label)
        
        # Cache with lock
        with self._cache_lock:
            self._migration_cache[cache_key] = result
        
        return result
    
    def _compute_migration_allowed(self, db: str, app_label: str) -> bool:
        """Compute if migration is allowed."""
        study_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        
        # Rule 1: Management apps only on default
        if app_label in self.MANAGEMENT_APPS:
            return db == 'default'
        
        # Rule 2: Study apps only on study databases
        if app_label in self.STUDY_APPS or app_label.startswith('study_'):
            if db == 'default':
                return False
            
            if not db.startswith(study_prefix):
                return False
            
            # Check database is configured
            from django.db import connections
            if db not in connections.databases:
                return False
            
            return True
        
        # Rule 3: Unknown apps - default rules
        if db == 'default':
            return not app_label.startswith('study_')
        
        if db.startswith(study_prefix):
            return app_label not in self.MANAGEMENT_APPS
        
        return False
    
    # =========================================================================
    # Cache Management
    # =========================================================================
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all caches."""
        with cls._cache_lock:
            cls._routing_cache.clear()
            cls._migration_cache.clear()
    
    @classmethod
    def invalidate_app(cls, app_label: str) -> None:
        """Invalidate cache for specific app."""
        with cls._cache_lock:
            cls._routing_cache.pop(app_label, None)
            # Also clear related migration cache entries
            keys_to_remove = [k for k in cls._migration_cache if k[1] == app_label]
            for key in keys_to_remove:
                cls._migration_cache.pop(key, None)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    @classmethod
    def is_management_app(cls, app_label: str) -> bool:
        """Check if app is a management app."""
        return app_label in cls.MANAGEMENT_APPS
    
    @classmethod
    def is_study_app(cls, app_label: str) -> bool:
        """Check if app is a study app."""
        return app_label in cls.STUDY_APPS or app_label.startswith('study_')
    
    @classmethod
    def get_app_database(cls, app_label: str) -> str:
        """Get expected database for an app."""
        if cls.is_management_app(app_label):
            return 'default'
        return get_current_db()


# =============================================================================
# Convenience Functions
# =============================================================================

def get_router_stats() -> Dict[str, Any]:
    """Get router cache statistics."""
    return {
        'routing_cache_size': len(TenantRouter._routing_cache),
        'migration_cache_size': len(TenantRouter._migration_cache),
        'cached_apps': list(TenantRouter._routing_cache.keys()),
    }


def clear_router_cache() -> None:
    """Clear router cache."""
    TenantRouter.clear_cache()