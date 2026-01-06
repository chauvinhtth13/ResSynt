"""
Database Study Creator - PostgreSQL database and schema management.

Uses psycopg3 with secure parameterized queries.
"""
import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

import environ
import psycopg
from psycopg import sql
from psycopg.errors import DuplicateDatabase, InsufficientPrivilege, InvalidCatalogName
from psycopg.rows import dict_row

from django.conf import settings

logger = logging.getLogger(__name__)


class DatabaseStudyCreator:
    """
    PostgreSQL database and schema management.
    
    Thread-safe with connection parameter caching.
    """
    
    _env: Optional[environ.Env] = None
    _lock = threading.Lock()
    
    # Valid database name pattern
    _VALID_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')
    
    @classmethod
    def get_env(cls) -> environ.Env:
        """Get cached environment instance."""
        if cls._env is None:
            cls._env = environ.Env()
        return cls._env
    
    @classmethod
    def get_connection_params(cls, db_name: str) -> Dict[str, Any]:
        """Get connection parameters for psycopg3."""
        env = cls.get_env()
        return {
            'host': env('PGHOST'),
            'port': env.int('PGPORT'),
            'user': env('PGUSER'),
            'password': env('PGPASSWORD'),
            'dbname': db_name,
            'connect_timeout': 10,
        }
    
    @classmethod
    def get_study_schemas(cls) -> List[str]:
        """Get list of schemas from environment."""
        from config.utils import parse_schemas
        return parse_schemas(cls.get_env()("STUDY_DB_SCHEMA", default="data"))
    
    @classmethod
    def _validate_db_name(cls, db_name: str) -> Tuple[bool, str]:
        """Validate database name for security."""
        if not db_name:
            return False, "Database name is required"
        
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        if not db_name.startswith(prefix):
            return False, f"Database name must start with '{prefix}'"
        
        if not cls._VALID_NAME_RE.match(db_name):
            return False, "Database name contains invalid characters"
        
        if len(db_name) > 63:
            return False, "Database name too long (max 63 characters)"
        
        # SQL keyword check
        keywords = {'select', 'insert', 'update', 'delete', 'drop', 'create', 
                   'alter', 'union', 'exec', 'execute'}
        if any(kw in db_name.lower() for kw in keywords):
            return False, "Database name contains restricted keywords"
        
        return True, ""
    
    @classmethod
    def database_exists(cls, db_name: str) -> bool:
        """Check if database exists."""
        try:
            with psycopg.connect(
                **cls.get_connection_params('postgres'),
                autocommit=True
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (db_name,)
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking database {db_name}: {type(e).__name__}")
            return False
    
    @classmethod
    def create_study_database(cls, db_name: str) -> Tuple[bool, str]:
        """
        Create database with required schemas.
        
        Thread-safe with lock to prevent race conditions.
        """
        # Validate name
        valid, error = cls._validate_db_name(db_name)
        if not valid:
            return False, error
        
        with cls._lock:
            # Check if exists (inside lock)
            if cls.database_exists(db_name):
                return cls.ensure_all_schemas(db_name)
            
            try:
                with psycopg.connect(
                    **cls.get_connection_params('postgres'),
                    autocommit=True
                ) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            sql.SQL("""
                                CREATE DATABASE {}
                                WITH ENCODING = 'UTF8'
                                LC_COLLATE = 'C'
                                LC_CTYPE = 'C'
                                TEMPLATE = template0
                            """).format(sql.Identifier(db_name))
                        )
                
                logger.info(f"Created database: {db_name}")
                
                # Create schemas
                success, msg = cls.ensure_all_schemas(db_name)
                if not success:
                    return False, f"Database created but schemas failed: {msg}"
                
                schemas = cls.get_study_schemas()
                return True, f"Database '{db_name}' created with schemas: {', '.join(schemas)}"
                
            except DuplicateDatabase:
                return cls.ensure_all_schemas(db_name)
            except InsufficientPrivilege as e:
                return False, f"Insufficient privileges: {e}"
            except psycopg.Error as e:
                return False, f"PostgreSQL error: {type(e).__name__}"
            except Exception as e:
                return False, f"Unexpected error: {type(e).__name__}"
    
    @classmethod
    def ensure_all_schemas(cls, db_name: str) -> Tuple[bool, str]:
        """Ensure all required schemas exist."""
        schemas = cls.get_study_schemas()
        created = []
        
        try:
            with psycopg.connect(
                **cls.get_connection_params(db_name),
                autocommit=True
            ) as conn:
                current_user = conn.info.user
                
                with conn.cursor() as cur:
                    for schema in schemas:
                        cur.execute(
                            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                            (schema,)
                        )
                        
                        if not cur.fetchone():
                            cur.execute(
                                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                                    sql.Identifier(schema)
                                )
                            )
                            cur.execute(
                                sql.SQL("GRANT ALL ON SCHEMA {} TO {}").format(
                                    sql.Identifier(schema),
                                    sql.Identifier(current_user)
                                )
                            )
                            cur.execute(
                                sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT ALL ON TABLES TO {}").format(
                                    sql.Identifier(schema),
                                    sql.Identifier(current_user)
                                )
                            )
                            created.append(schema)
                            logger.info(f"Created schema '{schema}' in {db_name}")
            
            if created:
                return True, f"Created schemas: {', '.join(created)}"
            return True, f"All schemas exist: {', '.join(schemas)}"
            
        except psycopg.Error as e:
            return False, f"Schema error: {type(e).__name__}"
        except Exception as e:
            return False, f"Unexpected error: {type(e).__name__}"
    
    @classmethod
    def drop_study_database(cls, db_name: str, force: bool = False) -> Tuple[bool, str]:
        """Drop a study database."""
        valid, error = cls._validate_db_name(db_name)
        if not valid:
            return False, f"Cannot drop: {error}"
        
        if not cls.database_exists(db_name):
            return True, f"Database {db_name} does not exist"
        
        try:
            with psycopg.connect(
                **cls.get_connection_params('postgres'),
                autocommit=True
            ) as conn:
                with conn.cursor() as cur:
                    if force:
                        cur.execute(
                            """
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = %s AND pid <> pg_backend_pid()
                            """,
                            (db_name,)
                        )
                    
                    cur.execute(
                        sql.SQL("DROP DATABASE IF EXISTS {}").format(
                            sql.Identifier(db_name)
                        )
                    )
            
            logger.info(f"Dropped database: {db_name}")
            return True, f"Database {db_name} dropped"
            
        except psycopg.Error as e:
            return False, f"Drop failed: {type(e).__name__}"
    
    @classmethod
    def get_database_info(cls, db_name: str) -> Optional[Dict[str, Any]]:
        """Get database metadata."""
        if not db_name or not cls.database_exists(db_name):
            return None
        
        try:
            with psycopg.connect(**cls.get_connection_params('postgres')) as conn:
                conn.read_only = True
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("""
                        SELECT
                            d.datname,
                            pg_encoding_to_char(d.encoding) AS encoding,
                            pg_database_size(d.oid) AS size_bytes,
                            r.rolname AS owner
                        FROM pg_database d
                        JOIN pg_roles r ON r.oid = d.datdba
                        WHERE d.datname = %s
                    """, (db_name,))
                    
                    row = cur.fetchone()
                    if not row:
                        return None
                    
                    from .backup_manager import format_size
                    info = dict(row)
                    info['size_human'] = format_size(info.get('size_bytes', 0))
                    info['schemas'] = cls.get_schema_info(db_name)
                    return info
                    
        except Exception as e:
            logger.error(f"Error getting database info: {type(e).__name__}")
            return None
    
    @classmethod
    def get_schema_info(cls, db_name: str) -> Dict[str, Any]:
        """Get schema information."""
        try:
            with psycopg.connect(**cls.get_connection_params(db_name)) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("""
                        SELECT 
                            s.schema_name,
                            COUNT(DISTINCT t.table_name) as table_count
                        FROM information_schema.schemata s
                        LEFT JOIN information_schema.tables t 
                            ON s.schema_name = t.table_schema
                            AND t.table_type = 'BASE TABLE'
                        WHERE s.schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                        GROUP BY s.schema_name
                    """)
                    
                    return {
                        row['schema_name']: {'table_count': row['table_count'] or 0}
                        for row in cur.fetchall()
                    }
        except Exception:
            return {}
    
    @classmethod
    def test_connection(cls, db_name: str) -> Tuple[bool, str]:
        """Test database connection."""
        try:
            with psycopg.connect(
                **cls.get_connection_params(db_name),
                connect_timeout=5
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    return True, f"Connected. {version[:50]}"
        except InvalidCatalogName:
            return False, f"Database '{db_name}' does not exist"
        except psycopg.OperationalError:
            return False, "Cannot connect to database"
        except Exception as e:
            return False, f"Error: {type(e).__name__}"