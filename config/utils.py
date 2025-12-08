"""
Configuration utilities using psycopg3
"""
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def load_study_apps() -> Tuple[List[str], bool]:
    """
    Load study apps with comprehensive error handling
    
    Returns:
        Tuple of (study_apps: List[str], has_errors: bool)
    """
    try:
        from backends.studies.study_loader import StudyAppLoader
        
        # Get study apps
        study_apps = StudyAppLoader.get_loadable_study_apps()
        
        if study_apps:
            logger.info(f"Loaded {len(study_apps)} study app(s)")
            return study_apps, False
        else:
            logger.debug("No study apps to load")
            return [], False

    except ImportError as e:
        logger.error(f"Failed to import study_loader: {e}")
        return [], True
    except Exception as e:
        logger.error(f"Error loading study apps: {e}")
        return [], True


class DatabaseConfig:
    """Centralized database configuration management"""

    REQUIRED_KEYS = {
        "ENGINE", "NAME", "USER", "PASSWORD", "HOST", "PORT",
        "ATOMIC_REQUESTS", "AUTOCOMMIT", "CONN_MAX_AGE",
        "CONN_HEALTH_CHECKS", "TIME_ZONE", "OPTIONS", "TEST",
    }

    DEFAULT_ENGINE = 'django.db.backends.postgresql'

    @classmethod
    def get_base_config(cls, env) -> Dict:
        """Get base connection info"""
        return {
            "ENGINE": cls.DEFAULT_ENGINE,
            "NAME": env("PGDATABASE"),
            "USER": env("PGUSER"),
            "PASSWORD": env("PGPASSWORD"),
            "HOST": env("PGHOST"),
            "PORT": env.int("PGPORT"),
        }

    @classmethod
    def add_default_settings(cls, config: Dict, conn_max_age: int = 0) -> Dict:
        """Add required Django settings"""
        config.update({
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": conn_max_age,
            "CONN_HEALTH_CHECKS": True,
            "TIME_ZONE": None,
            "OPTIONS": {},
            "TEST": {
                "CHARSET": None,
                "COLLATION": None,
                "NAME": None,
                "MIRROR": None,
            },
        })
        return config

    @classmethod
    def get_management_db(cls, env) -> Dict:
        """Get management database configuration"""
        config = cls.get_base_config(env)
        
        # Use longer connection age for management DB (frequently used)
        conn_max_age = 0 if env('DEBUG') else 600
        config = cls.add_default_settings(config, conn_max_age)
        
        # Management database specific OPTIONS
        management_schema = env("PGSCHEMA", default="tenancy")
        config["OPTIONS"] = {
            "options": f"-c search_path={management_schema},public",
            "sslmode": "allow",
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
            "application_name": "django_management",
        }
        
        cls.validate_config(config)
        return config

    @classmethod
    def get_study_db_config(cls, db_name: str, env) -> Dict:
        """
        Get study database configuration with all schemas
        
        Args:
            db_name: Study database name
            env: Environment variables
            
        Returns:
            Complete database configuration
        """
        # Get base config from management DB
        main_db = cls.get_management_db(env)
        
        # Study database specific settings
        config = {
            "ENGINE": cls.DEFAULT_ENGINE,
            "NAME": db_name,
            "USER": env("STUDY_PGUSER", default=main_db["USER"]),
            "PASSWORD": env("STUDY_PGPASSWORD", default=main_db["PASSWORD"]),
            "HOST": env("STUDY_PGHOST", default=main_db["HOST"]),
            "PORT": env.int("STUDY_PGPORT", default=main_db["PORT"]),
        }
        
        # Optimized connection settings for study databases
        conn_max_age = 0 if env('DEBUG') else 300  # 5 minutes for study DBs
        config = cls.add_default_settings(config, conn_max_age)
        
        # Parse and set up multiple schemas
        schemas = cls.parse_study_schemas(env)
        search_path = ','.join(schemas) + ',public'
        
        # Study database specific OPTIONS
        config["OPTIONS"] = {
            "options": f"-c search_path={search_path}",
            "sslmode": main_db["OPTIONS"]["sslmode"],
            "connect_timeout": 5,  # Faster timeout for study DBs
            "keepalives": 1,
            "keepalives_idle": 60,  # Longer idle for less used DBs
            "keepalives_interval": 10,
            "keepalives_count": 3,
            "application_name": f"django_study_{db_name}",
        }
        
        cls.validate_config(config, db_name)
        return config

    @classmethod
    def parse_study_schemas(cls, env) -> List[str]:
        """
        Parse study schemas from environment variable
        
        Returns:
            List of schema names
        """
        study_schemas_str = env('STUDY_DB_SCHEMA', default='data')
        
        if ',' in study_schemas_str:
            # Split by comma and strip whitespace
            return [s.strip() for s in study_schemas_str.split(',')]
        else:
            return [study_schemas_str.strip()]

    @classmethod
    def validate_config(cls, config: Dict, db_name: str = "default") -> None:
        """
        Validate database configuration has all required keys
        
        Args:
            config: Database configuration dictionary
            db_name: Database name for error messages
            
        Raises:
            ValueError: If required keys are missing
        """
        missing = cls.REQUIRED_KEYS - set(config.keys())
        if missing:
            raise ValueError(f"Database '{db_name}' missing keys: {sorted(missing)}")