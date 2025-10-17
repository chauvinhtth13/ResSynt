# backend/studies/study_loader.py - FIXED PYLANCE ERRORS
"""
Study App Loader - Dynamic study app discovery and loading

FEATURES:
- Discovers study folders in filesystem
- Queries active studies from database
- Verifies PostgreSQL databases exist
- Returns loadable apps for INSTALLED_APPS
- No persistent cache (fresh on each Python process)

FIXED:
- Pylance reportArgumentType errors for psycopg execute()
"""
import logging
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional, cast
import psycopg
from psycopg import sql  # ✅ Import sql module for type-safe queries
import environ

logger = logging.getLogger(__name__)


class StudyAppLoader:
    """
    Study app loader with intelligent discovery
    
    RESPONSIBILITIES:
    - Discover study folders in filesystem
    - Query active studies from database
    - Verify databases exist
    - Return loadable apps
    
    DESIGN:
    - No persistent cache (fresh each Python process)
    - Graceful error handling
    - Clear logging
    """
    
    # Paths
    STUDIES_BASE_DIR = Path(__file__).resolve().parent
    API_BASE_DIR = Path(__file__).resolve().parent.parent / 'api' / 'studies'
    
    # Constants
    STUDY_PREFIX = "study_"
    
    # ==========================================
    # FILESYSTEM DISCOVERY
    # ==========================================
    
    @classmethod
    def discover_study_folders(cls) -> Dict[str, Dict[str, bool]]:
        """
        Discover study folders in filesystem
        
        Looks for:
        - Database apps: backends/studies/study_[code]/
        - API apps: backends/api/studies/study_[code]/
        
        Returns:
            Dict mapping study_code to {database: bool, api: bool}
            
        Example:
            {
                '43en': {'database': True, 'api': True},
                '44en': {'database': True, 'api': False}
            }
        """
        study_info: Dict[str, Dict[str, bool]] = {}
        
        # Discover database apps
        if cls.STUDIES_BASE_DIR.exists():
            for folder in cls.STUDIES_BASE_DIR.iterdir():
                # Skip non-directories and non-study folders
                if not folder.is_dir():
                    continue
                
                if not folder.name.startswith(cls.STUDY_PREFIX):
                    continue
                
                # Check required files
                has_apps = (folder / 'apps.py').exists()
                has_init = (folder / '__init__.py').exists()
                
                if has_apps and has_init:
                    study_code = folder.name.replace(cls.STUDY_PREFIX, '')
                    
                    if study_code not in study_info:
                        study_info[study_code] = {'database': False, 'api': False}
                    
                    study_info[study_code]['database'] = True
                    logger.debug(f"Found database app: {folder.name}")
        
        # Discover API apps
        if cls.API_BASE_DIR.exists():
            for folder in cls.API_BASE_DIR.iterdir():
                if not folder.is_dir():
                    continue
                
                if not folder.name.startswith(cls.STUDY_PREFIX):
                    continue
                
                # Check required files
                has_urls = (folder / 'urls.py').exists()
                has_init = (folder / '__init__.py').exists()
                
                if has_urls and has_init:
                    study_code = folder.name.replace(cls.STUDY_PREFIX, '')
                    
                    if study_code not in study_info:
                        study_info[study_code] = {'database': False, 'api': False}
                    
                    study_info[study_code]['api'] = True
                    logger.debug(f"Found API app: {folder.name}")
        
        if study_info:
            logger.debug(
                f"Filesystem discovery: Found {len(study_info)} study folder(s)"
            )
        else:
            logger.debug("Filesystem discovery: No study folders found")
        
        return study_info
    
    # ==========================================
    # DATABASE DISCOVERY
    # ==========================================
    
    @classmethod
    def get_active_studies_from_database(cls) -> Set[str]:
        """
        Query database for active studies
        
        Connects to management database and queries study_information table.
        
        Returns:
            Set of active study codes (lowercase)
            Empty set if:
            - Database not accessible
            - Table doesn't exist
            - No active studies
            
        Example:
            {'43en', '44en'}
        """
        try:
            env = environ.Env()
            management_schema = env("PGSCHEMA")
            
            # Build connection string
            conninfo = (
                f"host={env('PGHOST')} "
                f"port={env.int('PGPORT')} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname={env('PGDATABASE')}"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # ✅ Fixed: Use sql.SQL() for type safety
                    # Set schema
                    cursor.execute(
                        sql.SQL("SET search_path TO {}, public").format(
                            sql.Identifier(str(management_schema))
                        )
                    )
                    
                    # Check if study_information table exists
                    cursor.execute(
                        sql.SQL("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = %s
                                AND table_name = 'study_information'
                            )
                        """),
                        (management_schema,)
                    )
                    
                    table_exists = cursor.fetchone()
                    if not table_exists or not table_exists[0]:
                        logger.debug(
                            f"Table '{management_schema}.study_information' not found. "
                            f"Run: python manage.py migrate"
                        )
                        return set()
                    
                    # Query active studies
                    cursor.execute(
                        sql.SQL("""
                            SELECT code 
                            FROM study_information 
                            WHERE status IN ('active', 'planning')
                            ORDER BY code
                        """)
                    )
                    
                    studies = {row[0].lower() for row in cursor.fetchall()}
                    
                    if studies:
                        logger.debug(
                            f"Database query: Found {len(studies)} active study/studies"
                        )
                    else:
                        logger.debug("Database query: No active studies found")
                    
                    return studies
                    
        except psycopg.OperationalError as e:
            logger.debug(f"Cannot connect to database: {e}")
            logger.debug("This is normal during initial setup")
            return set()
            
        except psycopg.Error as e:
            logger.debug(f"Database error: {e}")
            return set()
            
        except Exception as e:
            logger.warning(f"Unexpected error querying database: {e}")
            return set()
    
    @classmethod
    def verify_postgresql_database(cls, db_name: str) -> bool:
        """
        Verify that a PostgreSQL database exists
        
        Args:
            db_name: Database name (e.g., 'db_study_43en')
            
        Returns:
            True if database exists, False otherwise
        """
        try:
            env = environ.Env()
            
            # Connect to postgres database (always exists)
            conninfo = (
                f"host={env('PGHOST')} "
                f"port={env.int('PGPORT')} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # ✅ Fixed: Query with parameters (already type-safe)
                    cursor.execute(
                        sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
                        (db_name,)
                    )
                    
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        logger.debug(f"Database verification: '{db_name}' exists")
                        
                        # Ensure data schema exists
                        cls.ensure_data_schema(db_name)
                    else:
                        logger.debug(f"Database verification: '{db_name}' not found")
                    
                    return exists
                    
        except Exception as e:
            logger.debug(f"Error verifying database '{db_name}': {e}")
            return False
    
    @classmethod
    def ensure_data_schema(cls, db_name: str) -> bool:
        """
        Ensure 'data' schema exists in database
        
        Creates schema if it doesn't exist.
        
        Args:
            db_name: Database name
            
        Returns:
            True if schema exists or was created successfully
        """
        try:
            env = environ.Env()
            study_schema = env("STUDY_DB_SCHEMA")
            
            # Connect to study database
            conninfo = (
                f"host={env('PGHOST')} "
                f"port={env.int('PGPORT')} "
                f"user={env('PGUSER')} "
                f"password={env('PGPASSWORD')} "
                f"dbname={db_name}"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # ✅ Fixed: Query with parameters (already type-safe)
                    cursor.execute(
                        sql.SQL("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s"),
                        (study_schema,)
                    )
                    
                    if not cursor.fetchone():
                        # ✅ Fixed: Use sql.SQL() for dynamic schema name
                        cursor.execute(
                            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                                sql.Identifier(str(study_schema))
                            )
                        )
                        cursor.execute(
                            sql.SQL("GRANT ALL ON SCHEMA {} TO CURRENT_USER").format(
                                sql.Identifier(str(study_schema))
                            )
                        )
                        logger.info(
                            f"Created schema '{study_schema}' in database '{db_name}'"
                        )
                    else:
                        logger.debug(
                            f"Schema '{study_schema}' exists in database '{db_name}'"
                        )
            
            return True
            
        except Exception as e:
            logger.warning(
                f"Could not ensure schema in database '{db_name}': {e}"
            )
            return False
    
    # ==========================================
    # VALIDATION & FILTERING
    # ==========================================
    
    @classmethod
    def get_valid_studies(cls) -> Set[str]:
        """
        Get valid studies that can be loaded
        
        A study is valid if ALL of these are true:
        1. Folder exists in filesystem
        2. Study is active in database
        3. PostgreSQL database exists
        
        Returns:
            Set of valid study codes (lowercase)
            
        Example:
            {'43en', '44en'}
        """
        # Step 1: Discover folders
        folder_info = cls.discover_study_folders()
        
        # Step 2: Query active studies
        active_studies = cls.get_active_studies_from_database()
        
        # Early returns
        if not folder_info:
            logger.debug("No study folders found in filesystem")
            return set()
        
        if not active_studies:
            logger.debug("No active studies in database")
            return set()
        
        # Step 3: Find intersection (in both filesystem AND database)
        candidate_studies = set(folder_info.keys()) & active_studies
        
        if not candidate_studies:
            logger.debug(
                "No studies match criteria (folder exists + active in database)"
            )
            return set()
        
        # Step 4: Verify databases exist
        valid_studies: Set[str] = set()
        
        from django.conf import settings
        
        for study_code in sorted(candidate_studies):
            db_name = f"{settings.STUDY_DB_PREFIX}{study_code}"
            
            if cls.verify_postgresql_database(db_name):
                valid_studies.add(study_code)
                logger.debug(f"Study {study_code.upper()}: Valid and ready")
            else:
                logger.warning(
                    f"Study {study_code.upper()}: Database '{db_name}' not found. "
                    f"Create it via Django admin or run migrations."
                )
        
        if valid_studies:
            logger.info(f"Found {len(valid_studies)} valid study/studies to load")
        else:
            logger.debug("No valid studies to load")
        
        return valid_studies
    
    # ==========================================
    # APP GENERATION
    # ==========================================
    
    @classmethod
    def get_loadable_study_apps(cls) -> List[str]:
        """
        Get database apps for INSTALLED_APPS
        
        Returns only the database apps (not API apps).
        API apps are loaded separately via URL configuration.
        
        Returns:
            List of app paths for INSTALLED_APPS
            
        Example:
            [
                'backends.studies.study_43en',
                'backends.studies.study_44en'
            ]
        """
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            return []
        
        folder_info = cls.discover_study_folders()
        database_apps: List[str] = []
        
        for study_code in sorted(valid_studies):
            # Only include if database app exists
            if folder_info.get(study_code, {}).get('database'):
                db_app = f"backends.studies.{cls.STUDY_PREFIX}{study_code}"
                database_apps.append(db_app)
                logger.debug(f"Loadable app: {db_app}")
            else:
                logger.warning(
                    f"Study {study_code.upper()}: Database app folder missing. "
                    f"Run: python manage.py create_study_structure {study_code.upper()}"
                )
        
        if database_apps:
            logger.info(f"Returning {len(database_apps)} database app(s) for INSTALLED_APPS")
        
        return database_apps
    
    @classmethod
    def get_available_api_modules(cls) -> List[Tuple[str, str]]:
        """
        Get available API modules for URL configuration
        
        Returns:
            List of (study_code, api_module_path) tuples
            
        Example:
            [
                ('43en', 'backends.api.studies.study_43en.urls'),
                ('44en', 'backends.api.studies.study_44en.urls')
            ]
        """
        valid_studies = cls.get_valid_studies()
        
        if not valid_studies:
            return []
        
        folder_info = cls.discover_study_folders()
        api_modules: List[Tuple[str, str]] = []
        
        for study_code in sorted(valid_studies):
            # Only include if API app exists
            if folder_info.get(study_code, {}).get('api'):
                api_module = f"backends.api.studies.{cls.STUDY_PREFIX}{study_code}.urls"
                api_modules.append((study_code, api_module))
                logger.debug(f"API module: {study_code} to {api_module}")
        
        if api_modules:
            logger.debug(f"Found {len(api_modules)} API module(s)")
        
        return api_modules
    
    @classmethod
    def get_study_databases(cls) -> Dict[str, Dict]:
        """
        Get database configurations for all valid studies
        
        Returns:
            Dictionary mapping database names to their configurations
            
        Example:
            {
                'db_study_43en': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': 'db_study_43en',
                    'USER': 'postgres',
                    ...
                },
                'db_study_44en': { ... }
            }
        """
        from django.conf import settings
        from config.settings import DatabaseConfig
        
        databases: Dict[str, Dict] = {}
        database_apps = cls.get_loadable_study_apps()
        
        for app_path in database_apps:
            # Extract study code from app path
            # 'backends.studies.study_43en' → '43en'
            study_code = app_path.split('.')[-1].replace(cls.STUDY_PREFIX, '')
            
            # Generate database name
            db_name = f"{settings.STUDY_DB_PREFIX}{study_code}"
            
            # Get configuration
            databases[db_name] = DatabaseConfig.get_study_db_config(db_name)
            
            logger.debug(f"Database config: {db_name}")
        
        if databases:
            logger.info(f"Configured {len(databases)} study database(s)")
        
        return databases


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_loadable_apps() -> List[str]:
    """
    Get database apps for INSTALLED_APPS
    
    Convenience wrapper around StudyAppLoader.get_loadable_study_apps()
    
    Returns:
        List of app paths
        
    Example:
        >>> apps = get_loadable_apps()
        >>> print(apps)
        ['backends.studies.study_43en', 'backends.studies.study_44en']
    """
    return StudyAppLoader.get_loadable_study_apps()


def get_study_databases() -> Dict[str, Dict]:
    """
    Get database configurations
    
    Convenience wrapper around StudyAppLoader.get_study_databases()
    
    Returns:
        Dictionary of database configurations
        
    Example:
        >>> dbs = get_study_databases()
        >>> print(list(dbs.keys()))
        ['db_study_43en', 'db_study_44en']
    """
    return StudyAppLoader.get_study_databases()


def get_api_modules() -> List[Tuple[str, str]]:
    """
    Get API modules for URL configuration
    
    Convenience wrapper around StudyAppLoader.get_available_api_modules()
    
    Returns:
        List of (study_code, api_module_path) tuples
        
    Example:
        >>> modules = get_api_modules()
        >>> for code, module in modules:
        ...     print(f"{code}: {module}")
        43en: backends.api.studies.study_43en.urls
        44en: backends.api.studies.study_44en.urls
    """
    return StudyAppLoader.get_available_api_modules()