# backend/studies/study_loader.py - COMPLETE FIXED VERSION
"""
Study App Loader - Fixed to handle missing tables gracefully during initial setup

Changes from original:
1. Added table existence check before querying study_information
2. Improved error handling with DEBUG vs WARNING logs
3. Better user guidance messages
4. Graceful handling of missing tables during first startup
"""
import logging
from pathlib import Path
from typing import List, Set, Dict, Tuple
import psycopg
import environ

logger = logging.getLogger(__name__)


class StudyAppLoader:
    """
    Study app loader - separates database and API apps
    Gracefully handles missing tables during initial setup
    """
    
    STUDIES_BASE_DIR = Path(__file__).resolve().parent
    API_BASE_DIR = Path(__file__).resolve().parent.parent / 'api' / 'studies'
    STUDY_PREFIX = "study_"
    
    # Cache for valid studies
    _valid_studies_cache = None
    
    @classmethod
    def discover_study_folders(cls) -> Dict[str, Dict[str, bool]]:
        """Find all study folders (both database and API)"""
        study_info = {}
        
        # Check database app folders
        if cls.STUDIES_BASE_DIR.exists():
            for folder in cls.STUDIES_BASE_DIR.iterdir():
                if not folder.is_dir() or not folder.name.startswith(cls.STUDY_PREFIX):
                    continue
                
                if (folder / 'apps.py').exists() and (folder / '__init__.py').exists():
                    study_code = folder.name.replace(cls.STUDY_PREFIX, '')
                    if study_code not in study_info:
                        study_info[study_code] = {'database': False, 'api': False}
                    study_info[study_code]['database'] = True
        
        # Check API app folders
        if cls.API_BASE_DIR.exists():
            for folder in cls.API_BASE_DIR.iterdir():
                if not folder.is_dir() or not folder.name.startswith(cls.STUDY_PREFIX):
                    continue
                
                if (folder / 'urls.py').exists() and (folder / '__init__.py').exists():
                    study_code = folder.name.replace(cls.STUDY_PREFIX, '')
                    if study_code not in study_info:
                        study_info[study_code] = {'database': False, 'api': False}
                    study_info[study_code]['api'] = True
        
        if study_info:
            for code, info in study_info.items():
                status = []
                if info['database']:
                    status.append('DB')
                if info['api']:
                    status.append('API')
                logger.debug(f"Study {code.upper()}: {', '.join(status)} folders found")
        
        return study_info
    
    @classmethod
    def get_active_studies_from_database(cls) -> Set[str]:
        """
        Query database for active studies from management schema
        
        FIXED: Gracefully handles missing tables during initial setup
        
        Returns:
            Set of active study codes (lowercase)
        """
        try:
            env = environ.Env()
            management_schema = env("MANAGEMENT_DB_SCHEMA", default="management")
            
            conninfo = (
                f"host={env('PGHOST', default='localhost')} "
                f"port={env.int('PGPORT', default=5432)} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname={env('PGDATABASE')}"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {management_schema}, public")
                    
                    # FIXED: Check if table exists first
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = %s
                            AND table_name = 'study_information'
                        )
                    """, (management_schema,))
                    
                    table_exists = cursor.fetchone()[0]
                    
                    if not table_exists:
                        logger.debug(
                            f"Table '{management_schema}.study_information' does not exist yet. "
                            f"This is normal on first startup. Run: python manage.py migrate"
                        )
                        return set()
                    
                    # Table exists, query it
                    cursor.execute("""
                        SELECT code 
                        FROM study_information 
                        WHERE status IN ('active', 'planning')
                    """)
                    
                    studies = {row[0].lower() for row in cursor.fetchall()}
                    
                    if studies:
                        logger.info(f"Active studies in database: {sorted(studies)}")
                    else:
                        logger.debug("No active studies found in database")
                    
                    return studies
                    
        except psycopg.Error as e:
            # PostgreSQL-specific errors
            logger.debug(f"Database not ready: {e}")
            return set()
        except Exception as e:
            # Other errors (connection, etc.)
            logger.debug(f"Cannot query database: {e}")
            return set()
    
    @classmethod
    def verify_postgresql_database(cls, db_name: str) -> bool:
        """Verify PostgreSQL database exists and ensure schema"""
        try:
            env = environ.Env()
            
            conninfo = (
                f"host={env('PGHOST', default='localhost')} "
                f"port={env.int('PGPORT', default=5432)} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (db_name,)
                    )
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        cls.ensure_data_schema(db_name)
                    
                    return exists
                    
        except Exception as e:
            logger.error(f"Error checking database {db_name}: {e}")
            return False
    
    @classmethod
    def ensure_data_schema(cls, db_name: str):
        """Ensure 'data' schema exists in study database"""
        try:
            env = environ.Env()
            study_schema = env("STUDY_DB_SCHEMA", default="data")
            
            conninfo = (
                f"host={env('PGHOST', default='localhost')} "
                f"port={env.int('PGPORT', default=5432)} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname={db_name}"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                        (study_schema,)
                    )
                    
                    if not cursor.fetchone():
                        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {study_schema}")
                        logger.info(f"Created schema '{study_schema}' in database '{db_name}'")
                    
        except Exception as e:
            logger.warning(f"Could not ensure schema in {db_name}: {e}")
    
    @classmethod
    def get_valid_studies(cls) -> Set[str]:
        """
        Get valid studies (cached)
        
        FIXED: Better logging for troubleshooting
        
        Returns:
            Set of valid study codes (lowercase)
        """
        if cls._valid_studies_cache is not None:
            return cls._valid_studies_cache
        
        folder_info = cls.discover_study_folders()
        active_studies = cls.get_active_studies_from_database()
        
        # FIXED: Debug logging for troubleshooting
        if not folder_info:
            logger.debug("No study folders found in filesystem")
        
        if not active_studies:
            logger.debug(
                "No active studies found in database. "
                "This is normal on first startup before migrations are run."
            )
        
        if not folder_info or not active_studies:
            cls._valid_studies_cache = set()
            return cls._valid_studies_cache
        
        valid_studies = set()
        from django.conf import settings
        
        for study_code in (set(folder_info.keys()) & active_studies):
            db_name = f"{settings.STUDY_DB_PREFIX}{study_code}"
            if cls.verify_postgresql_database(db_name):
                valid_studies.add(study_code)
                logger.info(f"Loaded study: {study_code.upper()}")
            else:
                logger.warning(
                    f"Study {study_code.upper()} is active but database '{db_name}' not found"
                )
        
        if valid_studies:
            logger.info(f"Total valid studies loaded: {len(valid_studies)}")
        else:
            logger.debug("No valid studies to load at this time")
        
        cls._valid_studies_cache = valid_studies
        return valid_studies
    
    @classmethod
    def get_loadable_study_apps(cls) -> List[str]:
        """
        Get ONLY database apps for INSTALLED_APPS
        
        FIXED: Helpful instructions when no studies found
        
        Returns:
            List of app paths for INSTALLED_APPS
        """
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            logger.debug(
                "No study apps to load. To add studies:\n"
                "  1. Run: python manage.py migrate (to create study_information table)\n"
                "  2. Create a study in Django admin or via shell\n"
                "  3. Restart the server"
            )
            return []
        
        folder_info = cls.discover_study_folders()
        database_apps = []
        
        for study_code in sorted(valid_studies):
            if folder_info.get(study_code, {}).get('database'):
                db_app = f"backends.studies.{cls.STUDY_PREFIX}{study_code}"
                database_apps.append(db_app)
                logger.info(f"Loading database app: {db_app}")
            else:
                logger.warning(
                    f"Study {study_code.upper()} is active but database app folder not found. "
                    f"Run: python manage.py create_study_structure {study_code.upper()}"
                )
            
            if folder_info.get(study_code, {}).get('api'):
                logger.debug(f"API available: backends.api.studies.study_{study_code}")
        
        return database_apps
    
    @classmethod
    def get_available_api_modules(cls) -> List[Tuple[str, str]]:
        """
        Get available API modules for URL configuration
        Always returns a list (never None)
        
        Returns:
            List of (study_code, api_module_path) tuples
        """
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            logger.debug("No valid studies for API modules")
            return []  # Return empty list, not None
        
        folder_info = cls.discover_study_folders()
        api_modules = []
        
        for study_code in sorted(valid_studies):
            if folder_info.get(study_code, {}).get('api'):
                api_module = f"backends.api.studies.{cls.STUDY_PREFIX}{study_code}.urls"
                api_modules.append((study_code, api_module))
                logger.debug(f"API module ready: {study_code} -> {api_module}")
        
        if api_modules:
            logger.info(f"Found {len(api_modules)} API module(s)")
        
        return api_modules
    
    @classmethod
    def get_study_databases(cls) -> Dict[str, Dict]:
        """
        Get database configurations for loadable studies
        
        Returns:
            Dict mapping database names to their configurations
        """
        from django.conf import settings
        from config.settings import DatabaseConfig
        
        databases = {}
        database_apps = cls.get_loadable_study_apps()
        
        for app_path in database_apps:
            study_code = app_path.split('.')[-1].replace(cls.STUDY_PREFIX, '')
            db_name = f"{settings.STUDY_DB_PREFIX}{study_code}"
            
            databases[db_name] = DatabaseConfig.get_study_db_config(db_name)
            logger.debug(f"Configured database: {db_name}")
        
        return databases
    
    @classmethod
    def clear_cache(cls):
        """Clear valid studies cache"""
        cls._valid_studies_cache = None
        logger.debug("Cleared study loader cache")


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_loadable_apps() -> List[str]:
    """
    Get ONLY database apps for INSTALLED_APPS
    
    Returns:
        List of app paths
    """
    return StudyAppLoader.get_loadable_study_apps()


def get_study_databases() -> Dict[str, Dict]:
    """
    Get database configurations
    
    Returns:
        Dict of database configurations
    """
    return StudyAppLoader.get_study_databases()


def get_api_modules() -> List[Tuple[str, str]]:
    """
    Get API modules - ALWAYS returns list (never None)
    
    Returns:
        List of (study_code, api_module_path) tuples
    """
    return StudyAppLoader.get_available_api_modules()