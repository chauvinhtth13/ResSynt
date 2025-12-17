"""
Study Database Manager - Optimized with security hardening.

Features:
- Thread-safe singleton with minimal locking
- Secure SQL with parameterized queries
- Two-layer caching (instance + Django cache)
- Connection health monitoring
"""
import logging
from contextlib import contextmanager
from datetime import datetime
from threading import RLock
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import connections

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)


class StudyDatabaseManager:
    """
    Thread-safe database manager for multi-tenant study databases.
    
    Uses singleton pattern with lazy initialization.
    """
    
    _instance: Optional['StudyDatabaseManager'] = None
    _lock = RLock()
    
    CACHE_TTL = 600  # 10 minutes
    CACHE_PREFIX = "study_db_"
    
    def __new__(cls) -> 'StudyDatabaseManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._db_configs: Dict[str, Dict[str, Any]] = {}
        self._stats: Dict[str, Dict[str, Any]] = {}
        self._initialized = True
        
        logger.debug("StudyDatabaseManager initialized")
    
    # =========================================================================
    # Database Registration
    # =========================================================================
    
    def add_study_db(self, db_name: str) -> bool:
        """
        Register study database configuration.
        
        Args:
            db_name: Database name (e.g., 'db_study_43en')
            
        Returns:
            True if registered successfully
            
        Raises:
            ValueError: If database name is invalid
        """
        # Validate database name
        self._validate_db_name(db_name)
        
        # Fast path: already registered
        if db_name in connections.databases:
            self._track_usage(db_name, 'reuse')
            return True
        
        with self._lock:
            # Double-check after acquiring lock
            if db_name in connections.databases:
                return True
            
            # Get or build configuration
            config = self._get_config(db_name)
            
            # Register with Django
            connections.databases[db_name] = config
            
            # Initialize stats
            self._stats[db_name] = {
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'usage_count': 1,
                'errors': 0,
            }
            
            logger.debug(f"Registered database: {db_name}")
            return True
    
    def _validate_db_name(self, db_name: str) -> None:
        """Validate database name format and prefix."""
        if not db_name or not isinstance(db_name, str):
            raise ValueError("Database name must be a non-empty string")
        
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        if not db_name.startswith(prefix):
            raise ValueError(f"Invalid study database name: {db_name}")
        
        # Additional validation
        from config.utils import validate_identifier
        validate_identifier(db_name, "database name")
    
    # =========================================================================
    # Context Manager
    # =========================================================================
    
    @contextmanager
    def study_db_context(self, db_name: str):
        """
        Context manager for study database operations.
        
        Args:
            db_name: Database name
            
        Yields:
            Database connection wrapper
            
        Example:
            with manager.study_db_context('db_study_43en') as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM patients")
        """
        self.add_study_db(db_name)
        self._track_usage(db_name, 'context_enter')
        
        conn = connections[db_name]
        
        try:
            # Set search path securely
            schemas = self._get_schemas()
            with conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL("SET search_path TO {}").format(
                        sql.SQL(', ').join(map(sql.Identifier, schemas))
                    )
                )
            
            yield conn
            
        except Exception as e:
            self._track_error(db_name, e)
            raise
        finally:
            self._track_usage(db_name, 'context_exit')
    
    # =========================================================================
    # Schema Management
    # =========================================================================
    
    def ensure_schema_exists(self, db_name: str) -> bool:
        """
        Ensure required schemas exist in database.
        
        Args:
            db_name: Database name
            
        Returns:
            True if schemas exist or were created
        """
        try:
            self.add_study_db(db_name)
            schemas = self._get_schemas()
            
            config = connections.databases.get(db_name, {})
            
            with psycopg.connect(
                host=config.get('HOST'),
                port=config.get('PORT'),
                user=config.get('USER'),
                password=config.get('PASSWORD'),
                dbname=db_name,
                autocommit=True,
            ) as conn:
                with conn.cursor() as cur:
                    for schema in schemas:
                        # Check existence with parameterized query
                        cur.execute(
                            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                            (schema,)
                        )
                        
                        if not cur.fetchone():
                            # Create schema securely
                            cur.execute(
                                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                                    sql.Identifier(schema)
                                )
                            )
                            
                            # Grant permissions
                            cur.execute(
                                sql.SQL("GRANT ALL ON SCHEMA {} TO {}").format(
                                    sql.Identifier(schema),
                                    sql.Identifier(config.get('USER'))
                                )
                            )
                            
                            logger.info(f"Created schema '{schema}' in {db_name}")
            
            return True
            
        except psycopg.Error as e:
            logger.error(f"Database error for {db_name}: {type(e).__name__}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error for {db_name}: {type(e).__name__}")
            return False
    
    def _get_schemas(self) -> list:
        """Get list of schemas from settings."""
        from config.utils import parse_schemas
        import environ
        env = environ.Env()
        return parse_schemas(env("STUDY_DB_SCHEMA", default="data"))
    
    # =========================================================================
    # Health Check
    # =========================================================================
    
    def health_check(self, db_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Check health of study database(s).
        
        Args:
            db_name: Specific database to check, or None for all
            
        Returns:
            Health status dictionary
        """
        results = {}
        
        databases = [db_name] if db_name else self.get_registered_databases()
        
        for name in databases:
            result = {
                'status': 'UNKNOWN',
                'tables': 0,
                'error': None,
            }
            
            try:
                if name not in connections.databases:
                    result['status'] = 'NOT_REGISTERED'
                    continue
                
                conn = connections[name]
                
                if conn.ensure_connection():
                    with conn.cursor() as cursor:
                        # Check connection
                        cursor.execute("SELECT 1")
                        
                        # Count tables
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM information_schema.tables 
                            WHERE table_schema = 'data'
                            AND table_type = 'BASE TABLE'
                        """)
                        result['tables'] = cursor.fetchone()[0]
                        result['status'] = 'OK'
                else:
                    result['status'] = 'DISCONNECTED'
                    
            except Exception as e:
                result['status'] = 'ERROR'
                result['error'] = type(e).__name__
                
            results[name] = result
        
        return results
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def _get_config(self, db_name: str) -> Dict[str, Any]:
        """
        Get database configuration with two-layer caching.
        
        Layer 1: Instance cache (fastest)
        Layer 2: Django cache
        Layer 3: Build from settings
        """
        # Layer 1: Instance cache
        if db_name in self._db_configs:
            return self._db_configs[db_name]
        
        # Layer 2: Django cache
        cache_key = f"{self.CACHE_PREFIX}config_{db_name}"
        config = cache.get(cache_key)
        
        if config:
            self._db_configs[db_name] = config
            return config
        
        # Layer 3: Build configuration
        from config.utils import DatabaseConfig
        import environ
        env = environ.Env()
        
        config = DatabaseConfig.get_study_db_config(db_name, env)
        
        # Cache in both layers
        cache.set(cache_key, config, self.CACHE_TTL)
        self._db_configs[db_name] = config
        
        return config
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def _track_usage(self, db_name: str, action: str) -> None:
        """Track database usage."""
        if db_name in self._stats:
            self._stats[db_name]['last_used'] = datetime.now()
            self._stats[db_name]['usage_count'] += 1
    
    def _track_error(self, db_name: str, error: Exception) -> None:
        """Track database error."""
        if db_name in self._stats:
            self._stats[db_name]['errors'] += 1
            self._stats[db_name]['last_error'] = type(error).__name__
            self._stats[db_name]['last_error_time'] = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            'registered_count': len(self._db_configs),
            'databases': dict(self._stats),
        }
    
    def get_registered_databases(self) -> list:
        """Get list of registered study databases."""
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        return [
            name for name in connections.databases.keys()
            if name != 'default' and name.startswith(prefix)
        ]
    
    def is_registered(self, db_name: str) -> bool:
        """Check if database is registered."""
        return db_name in connections.databases
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        with self._lock:
            self._db_configs.clear()
            logger.debug("Cleared database configuration cache")


# =============================================================================
# Global Instance & Convenience Functions
# =============================================================================

study_db_manager = StudyDatabaseManager()


def get_study_db_manager() -> StudyDatabaseManager:
    """Get the global study database manager instance."""
    return study_db_manager


def register_study_database(db_name: str) -> None:
    """Register a study database."""
    study_db_manager.add_study_db(db_name)


def check_database_health() -> Dict[str, Any]:
    """Check health of all study databases."""
    return study_db_manager.health_check()