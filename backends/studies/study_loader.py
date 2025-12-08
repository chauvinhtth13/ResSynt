# backend/studies/study_loader.py - FIXED API MODULES
"""
Study App Loader - Fixed API module loading
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
        
        for code, info in study_info.items():
            status = []
            if info['database']:
                status.append('DB')
            if info['api']:
                status.append('API')
            logger.info(f"Study {code.upper()}: {', '.join(status)} folders found")
        
        return study_info
    
    @classmethod
    def get_active_studies_from_database(cls) -> Set[str]:
        """Query database for active studies from management schema"""
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
                    cursor.execute("""
                        SELECT code 
                        FROM study_information 
                        WHERE status IN ('active', 'planning')
                    """)
                    
                    studies = {row[0].lower() for row in cursor.fetchall()}
                    logger.info(f"Active studies in database: {sorted(studies)}")
                    return studies
                    
        except Exception as e:
            logger.warning(f"Cannot query database: {e}")
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
        """Ensure study schemas exist in study database"""
        try:
            env = environ.Env()
            study_schemas_str = env("STUDY_DB_SCHEMA", default="data")
            
            # Parse multiple schemas
            if ',' in study_schemas_str:
                schemas = [s.strip() for s in study_schemas_str.split(',')]
            else:
                schemas = [study_schemas_str.strip()]
            
            conninfo = (
                f"host={env('PGHOST', default='localhost')} "
                f"port={env.int('PGPORT', default=5432)} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname={db_name}"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    for schema in schemas:
                        cursor.execute(
                            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                            (schema,)
                        )
                        
                        if not cursor.fetchone():
                            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                            logger.info(f"Created schema '{schema}' in database '{db_name}'")
                    
        except Exception as e:
            logger.warning(f"Could not ensure schema in {db_name}: {e}")
    
    @classmethod
    def get_valid_studies(cls) -> Set[str]:
        """Get valid studies (cached)"""
        if cls._valid_studies_cache is not None:
            return cls._valid_studies_cache
        
        folder_info = cls.discover_study_folders()
        active_studies = cls.get_active_studies_from_database()
        
        if not folder_info or not active_studies:
            cls._valid_studies_cache = set()
            return cls._valid_studies_cache
        
        valid_studies = set()
        from django.conf import settings
        
        for study_code in (set(folder_info.keys()) & active_studies):
            db_name = f"{settings.STUDY_DB_PREFIX}{study_code}"
            if cls.verify_postgresql_database(db_name):
                valid_studies.add(study_code)
        
        cls._valid_studies_cache = valid_studies
        return valid_studies
    
    @classmethod
    def get_loadable_study_apps(cls) -> List[str]:
        """Get ONLY database apps for INSTALLED_APPS"""
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            logger.info("No valid studies to load")
            return []
        
        folder_info = cls.discover_study_folders()
        database_apps = []
        
        for study_code in sorted(valid_studies):
            if folder_info.get(study_code, {}).get('database'):
                db_app = f"backends.studies.{cls.STUDY_PREFIX}{study_code}"
                database_apps.append(db_app)
                logger.info(f"Loading database app: {db_app}")
            
            if folder_info.get(study_code, {}).get('api'):
                logger.info(f"API available: backends.api.studies.study_{study_code}")
        
        return database_apps
    
    @classmethod
    def get_available_api_modules(cls) -> List[Tuple[str, str]]:
        """
        Get available API modules for URL configuration
        Always returns a list (never None)
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
        
        logger.info(f"Found {len(api_modules)} API module(s)")
        return api_modules
    
    @classmethod
    def get_study_databases(cls) -> Dict[str, Dict]:
        """Get database configurations for loadable studies"""
        from django.conf import settings
        from config.utils import DatabaseConfig
        import environ
        
        databases = {}
        database_apps = cls.get_loadable_study_apps()
        env = environ.Env()
        
        for app_path in database_apps:
            study_code = app_path.split('.')[-1].replace(cls.STUDY_PREFIX, '')
            db_name = f"{settings.STUDY_DB_PREFIX}{study_code}"
            
            databases[db_name] = DatabaseConfig.get_study_db_config(db_name, env)
            logger.debug(f"Configured database: {db_name}")
        
        return databases
    
    @classmethod
    def clear_cache(cls):
        """Clear valid studies cache"""
        cls._valid_studies_cache = None


# Convenience functions - ALL RETURN PROPER TYPES
def get_loadable_apps() -> List[str]:
    """Get ONLY database apps for INSTALLED_APPS"""
    return StudyAppLoader.get_loadable_study_apps()

def get_study_databases() -> Dict[str, Dict]:
    """Get database configurations"""
    return StudyAppLoader.get_study_databases()

def get_api_modules() -> List[Tuple[str, str]]:
    """Get API modules - ALWAYS returns list"""
    return StudyAppLoader.get_available_api_modules()