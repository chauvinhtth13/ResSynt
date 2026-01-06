"""
Configuration utilities for database and study app management.
"""
import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Valid identifier pattern (PostgreSQL)
_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_identifier(name: str, context: str = "identifier") -> str:
    """
    Validate PostgreSQL identifier to prevent SQL injection.
    
    Args:
        name: Identifier to validate
        context: Description for error message
        
    Returns:
        Validated identifier
        
    Raises:
        ValueError: If identifier is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"Invalid {context}: must be non-empty string")
    
    name = name.strip()
    
    if len(name) > 63:  # PostgreSQL identifier limit
        raise ValueError(f"Invalid {context}: exceeds 63 characters")
    
    if not _IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Invalid {context}: contains invalid characters")
    
    # Block reserved/dangerous names
    reserved = {'pg_', 'information_schema', 'pg_catalog'}
    if any(name.lower().startswith(r) for r in reserved):
        raise ValueError(f"Invalid {context}: reserved name")
    
    return name


def parse_schemas(schema_str: str) -> List[str]:
    """
    Parse and validate comma-separated schema string.
    
    Args:
        schema_str: Comma-separated schema names
        
    Returns:
        List of validated schema names
    """
    if not schema_str:
        return ["public"]
    
    schemas = []
    for s in schema_str.split(','):
        s = s.strip()
        if s:
            schemas.append(validate_identifier(s, "schema"))
    
    return schemas if schemas else ["public"]


def load_study_apps() -> Tuple[List[str], bool]:
    """
    Load study apps with error handling.
    
    Returns:
        Tuple of (study_apps, has_errors)
    """
    try:
        from backends.studies.study_loader import StudyAppLoader
        study_apps = StudyAppLoader.get_loadable_study_apps()
        
        if study_apps:
            logger.info(f"Loaded {len(study_apps)} study app(s)")
        
        return study_apps, False
        
    except ImportError as e:
        logger.error(f"Failed to import study_loader: {e}")
        return [], True
    except Exception as e:
        # Don't expose internal details
        logger.error(f"Error loading study apps: {type(e).__name__}")
        return [], True


class DatabaseConfig:
    """Database configuration builder with security validation."""

    DEFAULT_ENGINE = 'django.db.backends.postgresql'
    
    REQUIRED_KEYS = frozenset({
        "ENGINE", "NAME", "USER", "PASSWORD", "HOST", "PORT",
        "ATOMIC_REQUESTS", "AUTOCOMMIT", "CONN_MAX_AGE",
        "CONN_HEALTH_CHECKS", "TIME_ZONE", "OPTIONS", "TEST",
    })

    @classmethod
    def _build_config(
        cls,
        db_name: str,
        user: str,
        password: str,
        host: str,
        port: int,
        conn_max_age: int,
        options: Dict,
    ) -> Dict:
        """Build complete database configuration."""
        return {
            "ENGINE": cls.DEFAULT_ENGINE,
            "NAME": db_name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": port,
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": conn_max_age,
            "CONN_HEALTH_CHECKS": True,
            "TIME_ZONE": None,
            "OPTIONS": options,
            "TEST": {
                "CHARSET": None,
                "COLLATION": None,
                "NAME": None,
                "MIRROR": None,
            },
        }

    @classmethod
    def _build_search_path(cls, schemas: List[str]) -> str:
        """Build validated search_path string."""
        validated = [validate_identifier(s, "schema") for s in schemas]
        return ','.join(validated + ['public'])

    @classmethod
    def get_management_db(cls, env) -> Dict:
        """Get management database configuration."""
        schema = env("MANAGEMENT_DB_SCHEMA", default="management")
        validated_schema = validate_identifier(schema, "management schema")
        
        conn_max_age = 0 if env.bool("DEBUG", default=False) else 600
        
        options = {
            "options": f"-c search_path={validated_schema},public",
            "sslmode": "prefer",  # Prefer SSL when available
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
            "application_name": "django_management",
        }
        
        config = cls._build_config(
            db_name=env("PGDATABASE"),
            user=env("PGUSER"),
            password=env("PGPASSWORD"),
            host=env("PGHOST"),
            port=env.int("PGPORT"),
            conn_max_age=conn_max_age,
            options=options,
        )
        
        cls.validate_config(config, "management")
        return config

    @classmethod
    def get_study_db_config(cls, db_name: str, env, management_db: Dict = None) -> Dict:
        """
        Get study database configuration.
        
        Args:
            db_name: Study database name (will be validated)
            env: Environment variables
            management_db: Optional cached management config
        """
        # Validate database name
        validate_identifier(db_name, "database name")
        
        if management_db is None:
            management_db = cls.get_management_db(env)
        
        # Inherit credentials from management DB if not specified
        user = env("STUDY_PGUSER", default="") or management_db["USER"]
        password = env("STUDY_PGPASSWORD", default="") or management_db["PASSWORD"]
        host = env("STUDY_PGHOST", default="") or management_db["HOST"]
        port = env.int("STUDY_PGPORT", default=0) or management_db["PORT"]
        
        # Build validated search path
        schemas = parse_schemas(env("STUDY_DB_SCHEMA", default="data"))
        search_path = cls._build_search_path(schemas)
        
        conn_max_age = 0 if env.bool("DEBUG", default=False) else 300
        
        options = {
            "options": f"-c search_path={search_path}",
            "sslmode": management_db["OPTIONS"].get("sslmode", "prefer"),
            "connect_timeout": 5,
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 3,
            "application_name": f"django_{db_name}",
        }
        
        config = cls._build_config(
            db_name=db_name,
            user=user,
            password=password,
            host=host,
            port=port,
            conn_max_age=conn_max_age,
            options=options,
        )
        
        cls.validate_config(config, db_name)
        return config

    @classmethod
    def validate_config(cls, config: Dict, db_name: str = "default") -> None:
        """Validate database configuration has all required keys."""
        missing = cls.REQUIRED_KEYS - set(config.keys())
        if missing:
            raise ValueError(f"Database '{db_name}' missing keys: {sorted(missing)}")