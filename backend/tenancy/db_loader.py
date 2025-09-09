# apps/tenancy/db_loader.py - OPTIMIZED
import logging
import weakref
from contextlib import contextmanager
from typing import Dict, Optional, Any
from django.db import connections, connection
from django.conf import settings
from django.core.cache import cache
from threading import RLock

from config.settings import DatabaseConfig

logger = logging.getLogger(__name__)

class StudyDatabaseManager:
    """Thread-safe study database connection manager with pooling"""
    
    _instance = None
    _lock = RLock()
    _connections: Dict[str, weakref.ref] = {}
    _usage_count: Dict[str, int] = {}
    
    CACHE_PREFIX = "study_db_"
    CACHE_TTL = 300  # 5 minutes
    MAX_CONNECTIONS = 20  # Maximum concurrent study DB connections
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def add_study_db(self, db_name: str) -> None:
        """Add study database with connection pooling and caching"""
        if not db_name.startswith(settings.STUDY_DB_PREFIX):
            raise ValueError(f"Invalid study DB name: {db_name}")
        
        with self._lock:
            # Check if already configured
            if db_name in connections.databases:
                self._usage_count[db_name] = self._usage_count.get(db_name, 0) + 1
                logger.debug(f"Study DB {db_name} already configured, usage: {self._usage_count[db_name]}")
                return
            
            # Check connection limit
            active_connections = sum(1 for ref in self._connections.values() if ref() is not None)
            if active_connections >= self.MAX_CONNECTIONS:
                self._cleanup_unused_connections()
            
            # Get config from cache or create new
            cache_key = f"{self.CACHE_PREFIX}{db_name}"
            config = cache.get(cache_key)
            
            if not config:
                config = DatabaseConfig.get_study_db_config(db_name)
                cache.set(cache_key, config, self.CACHE_TTL)
            
            # Add to Django connections
            connections.databases[db_name] = config
            self._usage_count[db_name] = 1
            
            # Track connection with weak reference
            if db_name in connections:
                self._connections[db_name] = weakref.ref(connections[db_name])
            
            logger.info(f"Added study DB: {db_name}")
    
    def remove_study_db(self, db_name: str) -> None:
        """Remove study database and close connections"""
        with self._lock:
            # Decrement usage count
            if db_name in self._usage_count:
                self._usage_count[db_name] -= 1
                
                # Only remove if no longer in use
                if self._usage_count[db_name] > 0:
                    logger.debug(f"Study DB {db_name} still in use: {self._usage_count[db_name]}")
                    return
                
                del self._usage_count[db_name]
            
            # Close connection if exists
            if db_name in connections:
                try:
                    connections[db_name].close()
                except Exception as e:
                    logger.error(f"Error closing connection {db_name}: {e}")
            
            # Remove from databases
            if db_name in connections.databases:
                del connections.databases[db_name]
            
            # Remove from tracking
            if db_name in self._connections:
                del self._connections[db_name]
            
            # Clear cache
            cache.delete(f"{self.CACHE_PREFIX}{db_name}")
            
            logger.info(f"Removed study DB: {db_name}")
    
    def _cleanup_unused_connections(self):
        """Clean up dead connections and least recently used"""
        with self._lock:
            # Remove dead references
            dead_refs = [name for name, ref in self._connections.items() if ref() is None]
            for name in dead_refs:
                self.remove_study_db(name)
            
            # Remove least used connections if still over limit
            if len(self._connections) >= self.MAX_CONNECTIONS:
                # Sort by usage count and remove least used
                sorted_dbs = sorted(self._usage_count.items(), key=lambda x: x[1])
                for db_name, _ in sorted_dbs[:5]:  # Remove up to 5 least used
                    if db_name != 'default':
                        self.remove_study_db(db_name)
    
    @contextmanager
    def study_db_context(self, db_name: str):
        """Context manager for study database usage"""
        self.add_study_db(db_name)
        try:
            yield connections[db_name]
        finally:
            # Don't immediately remove, let cleanup handle it
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                "active_connections": len(self._connections),
                "usage_counts": dict(self._usage_count),
                "max_connections": self.MAX_CONNECTIONS,
            }

# Global instance
study_db_manager = StudyDatabaseManager()

# Convenience functions for backward compatibility
def add_study_db(db_name: str) -> None:
    """Add study database configuration"""
    study_db_manager.add_study_db(db_name)

def remove_study_db(db_name: str) -> None:
    """Remove study database configuration"""
    study_db_manager.remove_study_db(db_name)

@contextmanager
def study_db_context(db_name: str):
    """Context manager for study database operations"""
    with study_db_manager.study_db_context(db_name) as conn:
        yield conn