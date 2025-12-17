"""
Study App Loader - Secure implementation with professional error handling.
"""
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

import environ
import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)


class DatabaseStatus(Enum):
    """Database initialization status."""
    OK = "ok"
    NOT_MIGRATED = "not_migrated"
    CONNECTION_ERROR = "connection_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class StudyInfo:
    """Study folder information."""
    code: str
    has_database_app: bool = False
    has_api_app: bool = False


@dataclass 
class LoaderCache:
    """Cache container for loader data."""
    folder_info: Optional[Dict[str, StudyInfo]] = None
    active_studies: Optional[Set[str]] = None
    valid_studies: Optional[Set[str]] = None
    existing_databases: Optional[Set[str]] = None
    db_status: DatabaseStatus = DatabaseStatus.OK
    
    def clear(self):
        self.folder_info = None
        self.active_studies = None
        self.valid_studies = None
        self.existing_databases = None
        self.db_status = DatabaseStatus.OK


class DatabaseConnection:
    """
    Secure context manager for database connections.
    
    - Uses parameterized queries
    - Sanitizes connection info in logs
    - Proper resource cleanup
    """
    
    def __init__(self, db_name: str = "postgres"):
        from config.utils import validate_identifier
        self.db_name = validate_identifier(db_name, "database name")
        self.conn: Optional[psycopg.Connection] = None
        self._env = environ.Env()
    
    def __enter__(self) -> psycopg.Connection:
        # Build connection parameters (not string) - more secure
        self.conn = psycopg.connect(
            host=self._env("PGHOST", default="localhost"),
            port=self._env.int("PGPORT", default=5432),
            user=self._env("PGUSER"),
            password=self._env("PGPASSWORD"),
            dbname=self.db_name,
            autocommit=True,
            connect_timeout=10,
        )
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass  # Ignore close errors


class StudyAppLoader:
    """
    Study app loader with security hardening and professional error messages.
    
    Security features:
    - SQL injection prevention via parameterized queries
    - Identifier validation
    - No sensitive data in logs
    - Graceful degradation on errors
    """
    
    STUDIES_BASE_DIR = Path(__file__).resolve().parent
    API_BASE_DIR = Path(__file__).resolve().parent.parent / 'api' / 'studies'
    STUDY_PREFIX = "study_"
    
    _cache = LoaderCache()
    
    # =========================================================================
    # Error Messages
    # =========================================================================
    
    MESSAGES = {
        DatabaseStatus.NOT_MIGRATED: (
            "Database not initialized: 'study_information' table missing.\n"
            "Run: python manage.py migrate\n"
            "For fresh setup: python manage.py loaddata initial_data"
        ),
        DatabaseStatus.CONNECTION_ERROR: (
            "Cannot connect to PostgreSQL database '{db_name}'.\n"
            "Check:\n"
            "1. PostgreSQL is running\n"
            "2. .env credentials are correct\n"
            "3. Database exists\n"
            "4. Network/firewall allows connection"
        ),
        DatabaseStatus.PERMISSION_ERROR: (
            "Permission denied for database.\n"
            "Check:\n"
            "1. PGUSER has correct permissions\n"
            "2. Schema '{schema}' is accessible"
        ),
    }
    
    # =========================================================================
    # Folder Discovery
    # =========================================================================
    
    @classmethod
    def discover_study_folders(cls) -> Dict[str, StudyInfo]:
        """Find all study folders (cached)."""
        if cls._cache.folder_info is not None:
            return cls._cache.folder_info
        
        studies: Dict[str, StudyInfo] = {}
        
        # Scan database app folders
        if cls.STUDIES_BASE_DIR.exists():
            for folder in cls.STUDIES_BASE_DIR.iterdir():
                if not cls._is_valid_study_folder(folder):
                    continue
                
                if (folder / 'apps.py').exists():
                    code = folder.name.removeprefix(cls.STUDY_PREFIX)
                    if code not in studies:
                        studies[code] = StudyInfo(code=code)
                    studies[code].has_database_app = True
        
        # Scan API app folders
        if cls.API_BASE_DIR.exists():
            for folder in cls.API_BASE_DIR.iterdir():
                if not cls._is_valid_study_folder(folder):
                    continue
                
                if (folder / 'urls.py').exists():
                    code = folder.name.removeprefix(cls.STUDY_PREFIX)
                    if code not in studies:
                        studies[code] = StudyInfo(code=code)
                    studies[code].has_api_app = True
        
        cls._cache.folder_info = studies
        return studies
    
    @classmethod
    def _is_valid_study_folder(cls, folder: Path) -> bool:
        """Check if folder is a valid study folder."""
        return (
            folder.is_dir() 
            and folder.name.startswith(cls.STUDY_PREFIX)
            and (folder / '__init__.py').exists()
        )
    
    # =========================================================================
    # Database Queries (Secure)
    # =========================================================================
    
    @classmethod
    def get_active_studies_from_database(cls) -> Set[str]:
        """Query active studies from management schema (cached)."""
        if cls._cache.active_studies is not None:
            return cls._cache.active_studies
        
        env = environ.Env()
        db_name = env("PGDATABASE")
        schema = env("MANAGEMENT_DB_SCHEMA", default="management")
        
        try:
            from config.utils import validate_identifier
            validated_schema = validate_identifier(schema, "schema")
            
            with DatabaseConnection(db_name) as conn:
                with conn.cursor() as cur:
                    # Use sql.Identifier for safe schema reference
                    cur.execute(
                        sql.SQL("SET search_path TO {}, public").format(
                            sql.Identifier(validated_schema)
                        )
                    )
                    
                    # Check if table exists first
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = %s 
                            AND table_name = 'study_information'
                        )
                    """, (validated_schema,))
                    
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        cls._cache.db_status = DatabaseStatus.NOT_MIGRATED
                        cls._log_status_message(DatabaseStatus.NOT_MIGRATED)
                        cls._cache.active_studies = set()
                        return set()
                    
                    # Table exists, query studies
                    cur.execute("""
                        SELECT LOWER(code) 
                        FROM study_information 
                        WHERE status IN ('active', 'planning')
                    """)
                    studies = {row[0] for row in cur.fetchall()}
            
            cls._cache.db_status = DatabaseStatus.OK
            
            if studies:
                logger.info(f"Active studies: {sorted(studies)}")
            else:
                logger.info("No active studies found in database")
            
            cls._cache.active_studies = studies
            return studies
            
        except psycopg.OperationalError as e:
            error_msg = str(e).lower()
            
            if "connection refused" in error_msg or "could not connect" in error_msg:
                cls._cache.db_status = DatabaseStatus.CONNECTION_ERROR
                cls._log_status_message(DatabaseStatus.CONNECTION_ERROR, db_name=db_name)
            elif "permission denied" in error_msg:
                cls._cache.db_status = DatabaseStatus.PERMISSION_ERROR
                cls._log_status_message(DatabaseStatus.PERMISSION_ERROR, schema=schema)
            else:
                cls._cache.db_status = DatabaseStatus.UNKNOWN_ERROR
                logger.error(f"Database error: {type(e).__name__}")
            
            cls._cache.active_studies = set()
            return set()
            
        except Exception as e:
            # Don't expose internal details in logs
            cls._cache.db_status = DatabaseStatus.UNKNOWN_ERROR
            logger.error(f"Unexpected error querying studies: {type(e).__name__}")
            cls._cache.active_studies = set()
            return set()
    
    @classmethod
    def _log_status_message(cls, status: DatabaseStatus, **kwargs) -> None:
        """Log formatted status message."""
        message = cls.MESSAGES.get(status, "")
        if message:
            formatted = message.format(**kwargs) if kwargs else message
            logger.warning(formatted)
    
    @classmethod
    def get_existing_databases(cls, db_names: List[str]) -> Set[str]:
        """Batch check which databases exist (single query)."""
        if not db_names:
            return set()
        
        if cls._cache.existing_databases is not None:
            return cls._cache.existing_databases & set(db_names)
        
        try:
            with DatabaseConnection("postgres") as conn:
                with conn.cursor() as cur:
                    # Parameterized query - safe from injection
                    placeholders = sql.SQL(',').join(sql.Placeholder() * len(db_names))
                    query = sql.SQL("SELECT datname FROM pg_database WHERE datname IN ({})").format(
                        placeholders
                    )
                    cur.execute(query, db_names)
                    existing = {row[0] for row in cur.fetchall()}
            
            cls._cache.existing_databases = existing
            return existing
            
        except Exception as e:
            logger.error(f"Error checking databases: {type(e).__name__}")
            return set()
    
    @classmethod
    def ensure_schemas(cls, db_name: str, schemas: List[str]) -> None:
        """Ensure schemas exist in database (secure)."""
        try:
            from config.utils import validate_identifier
            
            with DatabaseConnection(db_name) as conn:
                with conn.cursor() as cur:
                    for schema in schemas:
                        validated = validate_identifier(schema, "schema")
                        
                        # Check existence with parameterized query
                        cur.execute(
                            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                            (validated,)
                        )
                        
                        if not cur.fetchone():
                            # Create with identifier quoting
                            cur.execute(
                                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                                    sql.Identifier(validated)
                                )
                            )
                            logger.info(f"Created schema '{validated}' in '{db_name}'")
                            
        except Exception as e:
            logger.warning(f"Could not ensure schemas in {db_name}: {type(e).__name__}")
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    @classmethod
    def get_valid_studies(cls) -> Set[str]:
        """Get valid studies with existing databases (cached)."""
        if cls._cache.valid_studies is not None:
            return cls._cache.valid_studies
        
        folder_info = cls.discover_study_folders()
        active_studies = cls.get_active_studies_from_database()
        
        if not folder_info or not active_studies:
            cls._cache.valid_studies = set()
            return set()
        
        # Get study codes that have folders AND are active
        candidate_codes = set(folder_info.keys()) & active_studies
        
        if not candidate_codes:
            cls._cache.valid_studies = set()
            return set()
        
        # Build database names and batch check existence
        env = environ.Env()
        db_prefix = env("STUDY_DB_PREFIX", default="db_study_")
        
        db_name_to_code = {
            f"{db_prefix}{code}": code 
            for code in candidate_codes
        }
        
        existing_dbs = cls.get_existing_databases(list(db_name_to_code.keys()))
        
        # Map back to study codes
        valid_studies = {
            db_name_to_code[db_name] 
            for db_name in existing_dbs
        }
        
        # Ensure schemas for valid databases
        from config.utils import parse_schemas
        schemas = parse_schemas(env("STUDY_DB_SCHEMA", default="data"))
        
        for db_name in existing_dbs:
            cls.ensure_schemas(db_name, schemas)
        
        if valid_studies:
            logger.info(f"Valid studies: {sorted(valid_studies)}")
        
        cls._cache.valid_studies = valid_studies
        return valid_studies
    
    # =========================================================================
    # App Loading
    # =========================================================================
    
    @classmethod
    def get_loadable_study_apps(cls) -> List[str]:
        """Get database apps for INSTALLED_APPS."""
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            return []
        
        folder_info = cls.discover_study_folders()
        apps = []
        
        for code in sorted(valid_studies):
            info = folder_info.get(code)
            if info and info.has_database_app:
                app_path = f"backends.studies.{cls.STUDY_PREFIX}{code}"
                apps.append(app_path)
                logger.info(f"Loading: {app_path}")
        
        return apps
    
    @classmethod
    def get_available_api_modules(cls) -> List[Tuple[str, str]]:
        """Get API modules for URL configuration."""
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            return []
        
        folder_info = cls.discover_study_folders()
        modules = []
        
        for code in sorted(valid_studies):
            info = folder_info.get(code)
            if info and info.has_api_app:
                module_path = f"backends.api.studies.{cls.STUDY_PREFIX}{code}.urls"
                modules.append((code, module_path))
        
        return modules
    
    @classmethod
    def get_study_databases(cls) -> Dict[str, Dict]:
        """Get database configurations for valid studies."""
        from config.utils import DatabaseConfig
        
        valid_studies = cls.get_valid_studies()
        if not valid_studies:
            return {}
        
        env = environ.Env()
        db_prefix = env("STUDY_DB_PREFIX", default="db_study_")
        
        # Get management config once for inheritance
        management_db = DatabaseConfig.get_management_db(env)
        
        databases = {}
        for code in valid_studies:
            db_name = f"{db_prefix}{code}"
            databases[db_name] = DatabaseConfig.get_study_db_config(
                db_name, env, management_db
            )
        
        return databases
    
    @classmethod
    def get_database_status(cls) -> DatabaseStatus:
        """Get current database status."""
        return cls._cache.db_status
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all caches."""
        cls._cache.clear()


# =============================================================================
# Convenience Functions
# =============================================================================

def get_loadable_apps() -> List[str]:
    """Get database apps for INSTALLED_APPS."""
    return StudyAppLoader.get_loadable_study_apps()


def get_study_databases() -> Dict[str, Dict]:
    """Get database configurations."""
    return StudyAppLoader.get_study_databases()


def get_api_modules() -> List[Tuple[str, str]]:
    """Get API modules for URL routing."""
    return StudyAppLoader.get_available_api_modules()