# backend/tenancy/db_loader.py - FINAL PRODUCTION VERSION
"""
Enhanced Study Database Manager with psycopg3 support

Features:
- Instance-level and Django cache for database configurations
- Automatic schema setup (data schema)
- Connection pooling and health checks
- Thread-safe operations
- Usage statistics tracking
"""
import logging
from contextlib import contextmanager
from typing import Dict, Any
from datetime import datetime
from django.db import connections
from django.conf import settings
from config.settings import env
from django.core.cache import cache
from threading import RLock
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class EnhancedStudyDatabaseManager:
    """
    Database manager compatible with psycopg3
    Singleton pattern with thread-safe operations
    """
    
    _instance = None
    _lock = RLock()
    
    MAX_CONNECTIONS = 10
    CACHE_TTL = 600  # 10 minutes
    
    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize database manager"""
        if self._initialized:
            return
        
        self._db_configs: Dict[str, Dict[str, Any]] = {}
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        self._last_cleanup = datetime.now()
        self._initialized = True
        
        logger.debug("EnhancedStudyDatabaseManager initialized")
    
    # ==========================================
    # DATABASE REGISTRATION
    # ==========================================
    
    def add_study_db(self, db_name: str) -> None:
        """
        Add study database configuration
        Optimized with quick existence check
        
        Args:
            db_name: Database name (e.g., 'db_study_43en')
        """
        with self._lock:
            # Quick check if already registered
            if db_name in connections.databases:
                self._track_usage(db_name, 'reuse')
                logger.debug(f"Database {db_name} already registered")
                return
            
            # Validate database name
            if not db_name.startswith(settings.STUDY_DB_PREFIX):
                raise ValueError(f"Invalid study database name: {db_name}")
            
            # Get or build configuration
            config = self._get_config_with_schema(db_name)
            
            # Add to Django's connection registry
            connections.databases[db_name] = config
            
            # Track usage
            self._usage_stats[db_name] = {
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'usage_count': 1,
                'schema': 'data',
                'errors': 0,
            }
            
            logger.debug(f"Registered study database: {db_name} (schema: data)")
    
    # ==========================================
    # CONTEXT MANAGER
    # ==========================================
    
    @contextmanager
    def study_db_context(self, db_name: str):
        """
        Context manager for study database operations
        Ensures schema is set correctly
        
        Args:
            db_name: Database name
            
        Yields:
            Database connection
            
        Example:
            with study_db_manager.study_db_context('db_study_43en') as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM data.patients")
        """
        self.add_study_db(db_name)
        self._track_usage(db_name, 'context_enter')
        
        conn = connections[db_name]
        
        try:
            # Ensure schema is set for psycopg3
            with conn.cursor() as cursor:
                cursor.execute("SET search_path TO data, public")
            
            yield conn
            
        except Exception as e:
            self._track_error(db_name, e)
            logger.error(f"Error in study_db_context for {db_name}: {e}")
            raise
        finally:
            self._track_usage(db_name, 'context_exit')
    
    # ==========================================
    # SCHEMA MANAGEMENT
    # ==========================================
    
    def ensure_schema_exists(self, db_name: str) -> bool:
        """
        Ensure 'data' schema exists - PSYCOPG3 VERSION
        
        Args:
            db_name: Database name
            
        Returns:
            True if schema exists or was created
        """
        try:
            self.add_study_db(db_name)
            
            # Use DatabaseStudyCreator for consistency
            from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
            
            # Get connection params
            conn_params = DatabaseStudyCreator.get_connection_params(db_name)
            
            # Psycopg3 context manager with autocommit
            with psycopg.connect(**conn_params, autocommit=True) as conn:
                with conn.cursor() as cur:
                    # Check schema existence - parameterized
                    cur.execute(
                        """
                        SELECT schema_name 
                        FROM information_schema.schemata 
                        WHERE schema_name = %(schema_name)s
                        """,
                        {'schema_name': 'data'}
                    )
                    
                    if not cur.fetchone():
                        # Create schema safely
                        cur.execute(
                            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                                sql.Identifier('data')
                            )
                        )
                        
                        # Grant permissions using connection info
                        cur.execute(
                            sql.SQL("GRANT ALL ON SCHEMA {} TO {}").format(
                                sql.Identifier('data'),
                                sql.Identifier(conn.info.user)  # psycopg3 way
                            )
                        )
                        
                        logger.info(f"Created 'data' schema in {db_name}")
                    else:
                        logger.debug(f"Schema 'data' already exists in {db_name}")
            
            return True
            
        except psycopg.OperationalError as e:
            logger.error(f"Connection error for {db_name}: {e}")
            return False
        except psycopg.Error as e:
            logger.error(f"PostgreSQL error for {db_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error for {db_name}: {e}")
            return False
    
    # ==========================================
    # HEALTH CHECK
    # ==========================================
    
    def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Health check for all registered study databases
        
        Returns:
            Dictionary mapping database names to health status
        """
        results = {}
        
        with self._lock:
            for db_name in list(connections.databases.keys()):
                if db_name == 'default':
                    continue
                
                result = {
                    'status': 'UNKNOWN',
                    'schema': None,
                    'tables': 0,
                    'error': None,
                    'connected': False,
                }
                
                try:
                    # Get connection wrapper
                    conn_wrapper = connections[db_name]
                    
                    # Check if actually connected
                    if hasattr(conn_wrapper, 'connection') and conn_wrapper.connection is not None:
                        result['connected'] = True
                        
                        # Test connection
                        with conn_wrapper.cursor() as cursor:
                            cursor.execute("SELECT 1")
                            
                            # Check current schema
                            cursor.execute("SELECT current_schema()")
                            schema_row = cursor.fetchone()
                            result['schema'] = schema_row[0] if schema_row else None
                            
                            # Count tables in data schema
                            cursor.execute("""
                                SELECT COUNT(*) 
                                FROM information_schema.tables 
                                WHERE table_schema = 'data'
                                AND table_type = 'BASE TABLE'
                            """)
                            table_count = cursor.fetchone()
                            result['tables'] = table_count[0] if table_count else 0
                            
                            result['status'] = 'OK'
                    else:
                        result['status'] = 'NOT_CONNECTED'
                        
                except Exception as e:
                    result['status'] = 'ERROR'
                    result['error'] = str(e)
                    logger.error(f"Health check failed for {db_name}: {e}")
                
                results[db_name] = result
        
        return results
    
    # ==========================================
    # CONFIGURATION MANAGEMENT
    # ==========================================
    
    def _get_config_with_schema(self, db_name: str) -> Dict[str, Any]:
        """
        Build configuration with triple-layer caching
        
        Layer 1: Instance cache (fastest)
        Layer 2: Django cache (fast)
        Layer 3: Build from settings (slowest)
        
        Args:
            db_name: Database name
            
        Returns:
            Complete database configuration dictionary
        """
        # Layer 1: Instance cache
        if db_name in self._db_configs:
            logger.debug(f"Config cache hit (L1) for {db_name}")
            return self._db_configs[db_name]
        
        # Layer 2: Django cache
        cache_key = f"db_config_{db_name}"
        config = cache.get(cache_key)
        
        if config:
            logger.debug(f"Config cache hit (L2) for {db_name}")
            # Store in instance cache too
            self._db_configs[db_name] = config
            return config
        
        # Layer 3: Build configuration
        logger.debug(f"Building config for {db_name}")
        
        from config.settings import DatabaseConfig
        config = DatabaseConfig.get_study_db_config(db_name, env)
        
        # Ensure OPTIONS exists
        if 'OPTIONS' not in config:
            config['OPTIONS'] = {}

        # Set search_path for data schema
        config['OPTIONS']['options'] = '-c search_path=data,public'

        # Add psycopg3 specific options
        config['OPTIONS'].update({
            'prepare_threshold': None,
            'cursor_factory': None,
        })

        # Ensure all required keys exist
        config.setdefault('ATOMIC_REQUESTS', False)
        config.setdefault('AUTOCOMMIT', True)
        config.setdefault('CONN_MAX_AGE', 0 if settings.DEBUG else 600)
        config.setdefault('CONN_HEALTH_CHECKS', True)
        config.setdefault('TIME_ZONE', None)
        config.setdefault('TEST', {
            'CHARSET': None,
            'COLLATION': None,
            'NAME': None,
            'MIRROR': None,
        })
        
        # Cache in both layers
        cache.set(cache_key, config, self.CACHE_TTL)
        self._db_configs[db_name] = config
        
        return config
    
    # ==========================================
    # USAGE TRACKING
    # ==========================================
    
    def _track_usage(self, db_name: str, action: str):
        """Track database usage for statistics"""
        if db_name in self._usage_stats:
            self._usage_stats[db_name]['last_used'] = datetime.now()
            self._usage_stats[db_name]['usage_count'] = (
                self._usage_stats[db_name].get('usage_count', 0) + 1
            )
    
    def _track_error(self, db_name: str, error: Exception):
        """Track database errors for monitoring"""
        if db_name in self._usage_stats:
            stats = self._usage_stats[db_name]
            stats['errors'] = stats.get('errors', 0) + 1
            stats['last_error'] = str(error)
            stats['last_error_time'] = datetime.now()

    # ==========================================
    # STATISTICS & UTILITIES
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Returns:
            Dictionary with database statistics
        """
        with self._lock:
            return {
                'registered_databases': len(self._db_configs),
                'usage_stats': dict(self._usage_stats),
                'last_cleanup': self._last_cleanup.isoformat(),
                'cache_size': len(self._db_configs),
            }
    
    def print_stats(self):
        """Print formatted statistics (for debugging)"""
        stats = self.get_stats()
        
        output_lines = [
            "",
            "=" * 70,
            "STUDY DATABASE MANAGER STATISTICS",
            "=" * 70,
            f"Registered Databases: {stats['registered_databases']}",
            f"Cache Size: {stats['cache_size']}",
            f"Last Cleanup: {stats['last_cleanup']}",
        ]
        
        if stats['usage_stats']:
            output_lines.append("\nDatabase Usage:")
            for db_name, db_stats in stats['usage_stats'].items():
                output_lines.append(f"\n  {db_name}:")
                output_lines.append(f"    Usage Count: {db_stats.get('usage_count', 0)}")
                output_lines.append(f"    Errors: {db_stats.get('errors', 0)}")
                output_lines.append(f"    Last Used: {db_stats.get('last_used', 'Never')}")
                if 'last_error' in db_stats:
                    output_lines.append(f"    Last Error: {db_stats['last_error']}")
        
        output_lines.append("=" * 70 + "\n")
        
        # Use logger instead of print for production safety
        logger.info("\n".join(output_lines))

    def clear_cache(self):
        """Clear configuration cache (useful for testing)"""
        with self._lock:
            self._db_configs.clear()
            logger.debug("Cleared database configuration cache")
    
    def get_registered_databases(self) -> list:
        """
        Get list of registered study databases
        
        Returns:
            List of database names
        """
        with self._lock:
            return [
                db_name for db_name in connections.databases.keys()
                if db_name != 'default' and db_name.startswith(settings.STUDY_DB_PREFIX)
            ]
    
    def is_registered(self, db_name: str) -> bool:
        """
        Check if database is registered
        
        Args:
            db_name: Database name
            
        Returns:
            True if registered
        """
        return db_name in connections.databases


# ==========================================
# GLOBAL INSTANCE
# ==========================================

# Create singleton instance
study_db_manager = EnhancedStudyDatabaseManager()


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_study_db_manager() -> EnhancedStudyDatabaseManager:
    """
    Get the global study database manager instance
    
    Returns:
        EnhancedStudyDatabaseManager instance
    """
    return study_db_manager


def register_study_database(db_name: str) -> None:
    """
    Register a study database (convenience function)
    
    Args:
        db_name: Database name
    """
    study_db_manager.add_study_db(db_name)


def check_database_health() -> Dict[str, Dict[str, Any]]:
    """
    Check health of all study databases (convenience function)
    
    Returns:
        Health check results
    """
    return study_db_manager.health_check()