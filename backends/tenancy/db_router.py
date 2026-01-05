# backend/tenancy/db_router.py - PRODUCTION-READY VERSION
"""
Database Router for Multi-Tenant Study System

This router handles:
- Management apps (tenancy, auth, admin) -> default database
- Study apps (study_43en, study_44en, etc.) -> study-specific databases
- Thread-local database context switching
- Graceful handling of missing databases
- Performance optimization with caching
"""
import threading
from typing import Optional, Set, Dict, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


# ==========================================
# THREAD-LOCAL DATABASE CONTEXT
# ==========================================

_thread_local = threading.local()


def get_current_db() -> str:
    """
    Get current database for this thread
    
    Returns:
        Database alias (e.g., 'default', 'db_study_43en')
    """
    return getattr(_thread_local, 'db', 'default')


def set_current_db(db_alias: str) -> None:
    """
    Set current database for this thread
    
    Args:
        db_alias: Database alias to switch to
    """
    if db_alias and isinstance(db_alias, str):
        _thread_local.db = db_alias
        logger.debug(f"Thread {threading.current_thread().name}: switched to {db_alias}")
    else:
        _thread_local.db = 'default'
        logger.debug(f"Thread {threading.current_thread().name}: switched to default")


def clear_current_db() -> None:
    """Clear current database setting for this thread"""
    if hasattr(_thread_local, 'db'):
        del _thread_local.db
        logger.debug(f"Thread {threading.current_thread().name}: cleared database context")


# ==========================================
# DATABASE ROUTER
# ==========================================

class TenantRouter:
    """
    Multi-tenant database router with intelligent routing
    
    Features:
    - Automatic routing based on app labels
    - Thread-safe caching for performance
    - Graceful handling of missing databases
    - Support for cross-database operations
    - Debug utilities and statistics
    """
    
    # ==========================================
    # CLASS ATTRIBUTES (MUST BE DEFINED HERE)
    # ==========================================
    
    # Apps that MUST use management database
    MANAGEMENT_APPS: Set[str] = {
        'admin',           # Django admin
        'auth',            # Django authentication
        'contenttypes',    # Django content types
        'sessions',        # Django sessions
        'messages',        # Django messages
        'staticfiles',     # Django static files
        'tenancy',         # Our tenancy system
        'axes',            # django-axes (login protection)
        'usersessions',    # django-user-sessions
        'sites',           # Django sites framework
    }
    
    # Apps that use study databases
    STUDY_APPS: Set[str] = {
        'studies',         # Base studies app
        'audit_log',       # ✅ NEW: Base audit log system (shared across studies)
    }
    
    # Thread-safe routing cache
    _routing_cache: Dict[str, str] = {}
    _cache_lock = threading.Lock()
    
    # Migration allowance cache - CRITICAL for performance
    _migration_cache: Dict[tuple, bool] = {}
    _migration_cache_lock = threading.Lock()
    
    # Statistics
    _stats = {
        'cache_hits': 0,
        'cache_misses': 0,
        'routing_calls': 0,
        'migration_cache_hits': 0,
        'migration_cache_misses': 0,
    }
    
    def __init__(self):
        """Initialize router (for safety, ensure class attributes exist)"""
        # Ensure class attributes are properly set
        # (This is a safety measure for some Django versions)
        if not hasattr(self.__class__, 'MANAGEMENT_APPS'):
            self.__class__.MANAGEMENT_APPS = set(TenantRouter.MANAGEMENT_APPS)
        
        if not hasattr(self.__class__, 'STUDY_APPS'):
            self.__class__.STUDY_APPS = set(TenantRouter.STUDY_APPS)
        
        logger.debug(f"TenantRouter initialized with {len(self.MANAGEMENT_APPS)} management apps")
    
    # ==========================================
    # CORE ROUTING METHODS
    # ==========================================
    
    def _get_db_for_model(self, model) -> str:
        """
        Determine which database to use for a model
        
        Args:
            model: Django model class
            
        Returns:
            Database alias
        """
        app_label = model._meta.app_label
        
        # Update statistics
        self._stats['routing_calls'] += 1
        
        # Check cache with lock (fast path)
        with self._cache_lock:
            if app_label in self._routing_cache:
                self._stats['cache_hits'] += 1
                return self._routing_cache[app_label]
        
        # Cache miss - determine database
        self._stats['cache_misses'] += 1
        
        # Management apps always use default database
        if app_label in self.MANAGEMENT_APPS:
            db = 'default'
            logger.debug(f"Routing management app '{app_label}' to default database")
        
        # Study apps use current thread's database context
        elif app_label in self.STUDY_APPS or app_label.startswith('study_'):
            db = get_current_db()
            
            # Warn if study app is using default database (might be unintentional)
            if db == 'default':
                logger.debug(
                    f"Study app '{app_label}' using default DB "
                    f"(no study context set - this might be intentional during setup)"
                )
        
        # Unknown apps use current context
        else:
            db = get_current_db()
            logger.debug(f"Routing unknown app '{app_label}' to {db}")
        
        # Cache decision (thread-safe)
        with self._cache_lock:
            self._routing_cache[app_label] = db
        
        return db
    
    def db_for_read(self, model, **hints) -> str:
        """
        Suggest database for read operations
        
        Args:
            model: Model being read
            **hints: Additional routing hints
            
        Returns:
            Database alias
        """
        return self._get_db_for_model(model)
    
    def db_for_write(self, model, **hints) -> str:
        """
        Suggest database for write operations
        
        Args:
            model: Model being written
            **hints: Additional routing hints
            
        Returns:
            Database alias
        """
        return self._get_db_for_model(model)
    
    def allow_relation(self, obj1, obj2, **hints) -> Optional[bool]:
        """
        Determine if a relation between two objects is allowed
        
        Args:
            obj1: First object
            obj2: Second object
            **hints: Additional routing hints
            
        Returns:
            True if relation allowed, False if not, None if no opinion
        """
        db1 = self._get_db_for_model(obj1.__class__)
        db2 = self._get_db_for_model(obj2.__class__)
        
        # Relations only allowed within same database
        if db1 == db2:
            return True
        
        # Log cross-database relation attempts (these should be rare)
        logger.debug(
            f"Blocked cross-database relation: "
            f"{obj1.__class__.__name__} ({db1}) <-> "
            f"{obj2.__class__.__name__} ({db2})"
        )
        
        return False
    
    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints) -> bool:
        """
        Determine if migration is allowed
        
        Args:
            db: Database alias
            app_label: App label
            model_name: Model name (optional)
            **hints: Additional routing hints
            
        Returns:
            True if migration allowed, False otherwise
        """
        # Check cache first (CRITICAL for performance - called hundreds of times)
        cache_key = (db, app_label)
        with self._migration_cache_lock:
            if cache_key in self._migration_cache:
                self._stats['migration_cache_hits'] += 1
                return self._migration_cache[cache_key]
        
        # Cache miss - compute result
        self._stats['migration_cache_misses'] += 1
        
        # Get study database prefix
        study_db_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        
        # ==========================================
        # RULE 1: Management apps ONLY on default
        # ==========================================
        if app_label in self.MANAGEMENT_APPS:
            allowed = (db == 'default')
            
            if not allowed:
                logger.debug(
                    f"Blocked migration: Management app '{app_label}' "
                    f"cannot migrate to non-default database '{db}'"
                )
            
            # Cache and return
            with self._migration_cache_lock:
                self._migration_cache[cache_key] = allowed
            return allowed
        
        # ==========================================
        # RULE 2: Study apps ONLY on study databases
        # ==========================================
        if app_label in self.STUDY_APPS or app_label.startswith('study_'):
            # Cannot migrate to default database
            if db == 'default':
                logger.debug(
                    f"Blocked migration: Study app '{app_label}' "
                    f"cannot migrate to default database"
                )
                return False
            
            # Must be a study database
            if not db.startswith(study_db_prefix):
                logger.debug(
                    f"Blocked migration: Study app '{app_label}' "
                    f"can only migrate to study databases (prefix: {study_db_prefix})"
                )
                return False
            
            # Check if database is configured
            from django.db import connections
            
            if db not in connections.databases:
                logger.debug(
                    f"Database '{db}' not configured yet, "
                    f"skipping migration check for '{app_label}'"
                )
                return False
            
            # Check if database actually exists (graceful handling)
            if not self._database_exists(db):
                logger.debug(
                    f"Database '{db}' does not exist yet, "
                    f"skipping migration for '{app_label}'"
                )
                return False
            
            # All checks passed - allow migration
            with self._migration_cache_lock:
                self._migration_cache[cache_key] = True
            return True
        
        # ==========================================
        # RULE 3: Unknown apps - default rules
        # ==========================================
        
        # On default database - allow if not a study app
        if db == 'default':
            allowed = (
                app_label not in self.STUDY_APPS and 
                not app_label.startswith('study_')
            )
            with self._migration_cache_lock:
                self._migration_cache[cache_key] = allowed
            return allowed
        
        # On study database - allow if not a management app
        if db.startswith(study_db_prefix):
            allowed = app_label not in self.MANAGEMENT_APPS
            with self._migration_cache_lock:
                self._migration_cache[cache_key] = allowed
            return allowed
        
        # Unknown database - be conservative
        logger.warning(f"Unknown database '{db}' - denying migration for '{app_label}'")
        with self._migration_cache_lock:
            self._migration_cache[cache_key] = False
        return False
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _database_exists(self, db_name: str) -> bool:
        """
        Check if a database exists
        
        Args:
            db_name: Database name
            
        Returns:
            True if database exists, False otherwise
        """
        try:
            # Try to import DatabaseCreator
            from backends.tenancy.utils import DatabaseStudyCreator
            
            return DatabaseStudyCreator.database_exists(db_name)
            
        except ImportError:
            # DatabaseCreator not available yet (during initial setup)
            logger.debug(
                f"Cannot check database existence for '{db_name}' "
                f"(DatabaseStudyCreator not available yet)"
            )
            # Assume it exists and let Django handle any errors
            return True
            
        except Exception as e:
            # Some other error - log and assume exists
            logger.debug(f"Could not verify database '{db_name}': {e}")
            return True
    
    # ==========================================
    # CACHE MANAGEMENT
    # ==========================================
    
    @classmethod
    def clear_cache(cls):
        """Clear ALL caches (routing + migration) - thread-safe"""
        with cls._cache_lock:
            routing_count = len(cls._routing_cache)
            cls._routing_cache.clear()
        
        with cls._migration_cache_lock:
            migration_count = len(cls._migration_cache)
            cls._migration_cache.clear()
        
        logger.debug(
            f"Cleared caches: {routing_count} routing, {migration_count} migration entries"
        )
    
    @classmethod
    def invalidate_app(cls, app_label: str):
        """
        Invalidate cache for specific app
        
        Args:
            app_label: App label to invalidate
        """
        with cls._cache_lock:
            removed = cls._routing_cache.pop(app_label, None)
            if removed:
                logger.debug(f"Invalidated routing cache for '{app_label}'")
    
    @classmethod
    def invalidate_apps(cls, app_labels: Set[str]):
        """
        Bulk invalidate cache for multiple apps
        
        Args:
            app_labels: Set of app labels to invalidate
        """
        with cls._cache_lock:
            for app_label in app_labels:
                cls._routing_cache.pop(app_label, None)
            logger.debug(f"Invalidated routing cache for {len(app_labels)} apps")
    
    # ==========================================
    # STATISTICS & DEBUGGING
    # ==========================================
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        with cls._cache_lock:
            cache_size = len(cls._routing_cache)
            cached_apps = list(cls._routing_cache.keys())
        
        with cls._migration_cache_lock:
            migration_cache_size = len(cls._migration_cache)
        
        return {
            'routing_cache_size': cache_size,
            'migration_cache_size': migration_cache_size,
            'cached_apps': cached_apps,
            'management_apps': list(cls.MANAGEMENT_APPS),
            'study_apps': list(cls.STUDY_APPS),
            'cache_hits': cls._stats['cache_hits'],
            'cache_misses': cls._stats['cache_misses'],
            'routing_calls': cls._stats['routing_calls'],
            'migration_cache_hits': cls._stats['migration_cache_hits'],
            'migration_cache_misses': cls._stats['migration_cache_misses'],
            'routing_hit_rate': (
                cls._stats['cache_hits'] / cls._stats['routing_calls'] * 100
                if cls._stats['routing_calls'] > 0 else 0
            ),
            'migration_hit_rate': (
                cls._stats['migration_cache_hits'] / 
                (cls._stats['migration_cache_hits'] + cls._stats['migration_cache_misses']) * 100
                if (cls._stats['migration_cache_hits'] + cls._stats['migration_cache_misses']) > 0 
                else 0
            ),
        }
    
    @classmethod
    def reset_stats(cls):
        """Reset statistics"""
        cls._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'routing_calls': 0,
            'migration_cache_hits': 0,
            'migration_cache_misses': 0,
        }
        logger.debug("Reset routing statistics")
    
    @classmethod
    def print_stats(cls):
        """Print routing statistics (for debugging)"""
        stats = cls.get_cache_stats()
        
        print("\n" + "=" * 70)
        print("DATABASE ROUTER STATISTICS")
        print("=" * 70)
        print(f"Cache Size: {stats['cache_size']} apps")
        print(f"Routing Calls: {stats['routing_calls']}")
        print(f"Cache Hits: {stats['cache_hits']}")
        print(f"Cache Misses: {stats['cache_misses']}")
        print(f"Hit Rate: {stats['hit_rate']:.1f}%")
        print("\nManagement Apps:", ", ".join(sorted(stats['management_apps'])))
        print("Study Apps:", ", ".join(sorted(stats['study_apps'])))
        print("\nCached Apps:", ", ".join(sorted(stats['cached_apps'])))
        print("=" * 70 + "\n")
    
    @classmethod
    def is_management_app(cls, app_label: str) -> bool:
        """Check if app is a management app"""
        return app_label in cls.MANAGEMENT_APPS
    
    @classmethod
    def is_study_app(cls, app_label: str) -> bool:
        """Check if app is a study app"""
        return app_label in cls.STUDY_APPS or app_label.startswith('study_')
    
    @classmethod
    def get_app_database(cls, app_label: str) -> str:
        """
        Get expected database for an app
        
        Args:
            app_label: App label
            
        Returns:
            Expected database alias
        """
        if cls.is_management_app(app_label):
            return 'default'
        elif cls.is_study_app(app_label):
            return get_current_db()
        else:
            return get_current_db()


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_router_stats() -> Dict[str, Any]:
    """
    Get router statistics (convenience function)
    
    Returns:
        Dictionary with router statistics
    """
    return TenantRouter.get_cache_stats()


def print_router_stats():
    """Print router statistics (convenience function)"""
    TenantRouter.print_stats()


def clear_router_cache():
    """Clear router cache (convenience function)"""
    TenantRouter.clear_cache()