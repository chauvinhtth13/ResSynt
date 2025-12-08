"""
Database Study Creator - Using psycopg3 exclusively
https://www.psycopg.org/psycopg3/docs/
"""
import logging
from typing import Tuple, Dict, List, Any, Optional, cast
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.errors import DuplicateDatabase, InvalidCatalogName, InsufficientPrivilege
import environ
from django.conf import settings

logger = logging.getLogger(__name__)


class DatabaseStudyCreator:
    """
    PostgreSQL database and schema management using psycopg3
    """
    
    _env = None
    
    @classmethod
    def get_env(cls):
        """Get cached environment instance"""
        if cls._env is None:
            cls._env = environ.Env()
        return cls._env
    
    
    @classmethod
    def get_connection_params(cls, db_name: str) -> Dict[str, Any]:
        """
        Get connection parameters for psycopg3
        
        Args:
            db_name: Target database name
            
        Returns:
            Dictionary of connection parameters
        """
        env = cls.get_env()
        
        return {
            'host': env('PGHOST'),
            'port': env.int('PGPORT'),
            'user': env('PGUSER'),
            'password': env('PGPASSWORD'),
            'dbname': db_name,
            'connect_timeout': 10,
            'application_name': f'django_db_creator_{db_name}',
        }
    
    @classmethod
    def get_connection_string(cls, db_name: str) -> str:
        """
        Build PostgreSQL connection string for psycopg3
        
        Args:
            db_name: Target database name
            
        Returns:
            Connection string
        """
        params = cls.get_connection_params(db_name)
        return (
            f"host={params['host']} "
            f"port={params['port']} "
            f"user={params['user']} "
            f"password={params['password']} "
            f"dbname={params['dbname']} "
            f"connect_timeout={params['connect_timeout']} "
            f"application_name={params['application_name']}"
        )
    
    @classmethod
    def get_study_schemas(cls) -> List[str]:
        """
        Get list of schemas from environment variable
        
        Returns:
            List of schema names to create
        """
        env = cls.get_env()
        study_schemas_str = cast(str, env.str("STUDY_DB_SCHEMA"))
        
        if ',' in study_schemas_str:
            return [s.strip() for s in study_schemas_str.split(',')]
        else:
            return [study_schemas_str.strip()]
    
    @classmethod
    def database_exists(cls, db_name: str) -> bool:
        """
        Check if database exists using psycopg3
        
        Args:
            db_name: Database name to check
            
        Returns:
            True if database exists
        """
        try:
            # Use psycopg3 connection with context manager
            with psycopg.connect(
                **cls.get_connection_params('postgres'),
                autocommit=True
            ) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # Parameterized query - psycopg3 style
                    cur.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %(dbname)s",
                        {'dbname': db_name}
                    )
                    return cur.fetchone() is not None
                    
        except psycopg.OperationalError as e:
            logger.error(f"Cannot connect to PostgreSQL: {e}")
            return False
        except psycopg.Error as e:
            logger.error(f"Database error checking {db_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    @classmethod
    def create_study_database(cls, db_name: str) -> Tuple[bool, str]:
        """
        Create database with all required schemas using psycopg3
        🔒 SECURITY FIX: Thread-safe to prevent race conditions
        
        Args:
            db_name: Database name to create
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # 🔒 SECURITY FIX: Enhanced database name validation
            if not db_name.startswith(settings.STUDY_DB_PREFIX):
                return False, f"Database name must start with '{settings.STUDY_DB_PREFIX}'"
            
            # Strict alphanumeric check (only letters, numbers, underscores, hyphens)
            import re
            if not re.match(r'^[a-z0-9_-]+$', db_name.lower()):
                return False, "Database name contains invalid characters (only a-z, 0-9, _, - allowed)"
            
            # SQL keyword blacklist to prevent injection
            sql_keywords = {'select', 'insert', 'update', 'delete', 'drop', 'create', 
                           'alter', 'union', 'exec', 'execute', 'declare', 'or', 'and'}
            db_name_lower = db_name.lower()
            if any(keyword in db_name_lower for keyword in sql_keywords):
                return False, "Database name contains restricted SQL keywords"
            
            if len(db_name) > 63:  # PostgreSQL limit
                return False, "Database name too long (max 63 characters)"
            
            # 🔒 CRITICAL: Lock to prevent race condition (check-then-create)
            with cls._db_creation_lock:
                # Check if already exists (inside lock)
                if cls.database_exists(db_name):
                    logger.info(f"Database {db_name} already exists")
                    # Ensure schemas exist
                    return cls.ensure_all_schemas(db_name)
                
                # Create database using psycopg3
                with psycopg.connect(
                    **cls.get_connection_params('postgres'),
                    autocommit=True  # Required for CREATE DATABASE
                ) as conn:
                    with conn.cursor() as cur:
                        # Use sql module for safe identifier handling
                        query = sql.SQL("""
                            CREATE DATABASE {dbname}
                            WITH 
                            ENCODING = 'UTF8'
                            LC_COLLATE = 'C'
                            LC_CTYPE = 'C'
                            CONNECTION LIMIT = -1
                            TEMPLATE = template0
                        """).format(dbname=sql.Identifier(db_name))
                        # Note: Using 'C' collation for cross-platform compatibility
                        # Windows would use 'English_United States.1252' if we used system locale
                        
                        cur.execute(query)
                        logger.info(f"Created database: {db_name}")
                
                # Create all schemas in new database (still inside lock)
                success, message = cls.ensure_all_schemas(db_name)
                if not success:
                    return False, f"Database created but schemas failed: {message}"
                
                schemas = cls.get_study_schemas()
                return True, f"Database '{db_name}' created with schemas: {', '.join(schemas)}"
            
        except DuplicateDatabase:
            # Database was created between check and create
            logger.info(f"Database {db_name} already exists (race condition)")
            return cls.ensure_all_schemas(db_name)
            
        except InsufficientPrivilege as e:
            error_msg = f"Insufficient privileges to create database: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except psycopg.Error as e:
            error_msg = f"PostgreSQL error: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    @classmethod
    def ensure_all_schemas(cls, db_name: str) -> Tuple[bool, str]:
        """
        Ensure all required schemas exist using psycopg3
        
        Args:
            db_name: Database name
            
        Returns:
            Tuple of (success, message)
        """
        schemas = cls.get_study_schemas()
        created_schemas = []
        existing_schemas = []
        
        try:
            # Connect with psycopg3
            with psycopg.connect(
                **cls.get_connection_params(db_name),
                autocommit=True
            ) as conn:
                with conn.cursor() as cur:
                    for schema_name in schemas:
                        # Check if schema exists - parameterized query
                        cur.execute(
                            """
                            SELECT schema_name 
                            FROM information_schema.schemata 
                            WHERE schema_name = %(schema)s
                            """,
                            {'schema': schema_name}
                        )
                        
                        if not cur.fetchone():
                            # Create schema using sql.Identifier for safety
                            cur.execute(
                                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                                    sql.Identifier(schema_name)
                                )
                            )
                            
                            # Grant permissions - get current user from connection
                            current_user = conn.info.user
                            
                            cur.execute(
                                sql.SQL("GRANT ALL ON SCHEMA {} TO {}").format(
                                    sql.Identifier(schema_name),
                                    sql.Identifier(current_user)
                                )
                            )
                            
                            # Set default privileges for future tables
                            cur.execute(
                                sql.SQL("""
                                    ALTER DEFAULT PRIVILEGES IN SCHEMA {}
                                    GRANT ALL ON TABLES TO {}
                                """).format(
                                    sql.Identifier(schema_name),
                                    sql.Identifier(current_user)
                                )
                            )
                            
                            # Set default privileges for sequences
                            cur.execute(
                                sql.SQL("""
                                    ALTER DEFAULT PRIVILEGES IN SCHEMA {}
                                    GRANT ALL ON SEQUENCES TO {}
                                """).format(
                                    sql.Identifier(schema_name),
                                    sql.Identifier(current_user)
                                )
                            )
                            
                            created_schemas.append(schema_name)
                            logger.info(f"Created schema '{schema_name}' in {db_name}")
                        else:
                            existing_schemas.append(schema_name)
                            logger.debug(f"Schema '{schema_name}' already exists in {db_name}")
                    
                    # Build result message
                    all_schemas = ', '.join(schemas)
                    if created_schemas and existing_schemas:
                        return True, f"Schemas ready: {all_schemas} (created: {', '.join(created_schemas)})"
                    elif created_schemas:
                        return True, f"Created schemas: {', '.join(created_schemas)}"
                    else:
                        return True, f"All schemas exist: {all_schemas}"
                    
        except psycopg.OperationalError as e:
            error_msg = f"Cannot connect to database {db_name}: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except InsufficientPrivilege as e:
            error_msg = f"Insufficient privileges for schema operations: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except psycopg.Error as e:
            error_msg = f"PostgreSQL error: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    @classmethod
    def drop_study_database(cls, db_name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Drop a study database using psycopg3
        
        Args:
            db_name: Database name to drop
            force: Force termination of active connections
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate database name
            if not db_name.startswith(settings.STUDY_DB_PREFIX):
                return False, f"Cannot drop non-study database: {db_name}"
            
            # Check if exists
            if not cls.database_exists(db_name):
                return True, f"Database {db_name} does not exist"
            
            with psycopg.connect(
                **cls.get_connection_params('postgres'),
                autocommit=True
            ) as conn:
                with conn.cursor() as cur:
                    if force:
                        # Terminate all connections using parameterized query
                        cur.execute(
                            """
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = %(dbname)s
                            AND pid <> pg_backend_pid()
                            """,
                            {'dbname': db_name}
                        )
                        
                        terminated = cur.fetchall()
                        if terminated:
                            logger.info(f"Terminated {len(terminated)} connections to {db_name}")
                    
                    # Drop database using sql.Identifier
                    cur.execute(
                        sql.SQL("DROP DATABASE IF EXISTS {}").format(
                            sql.Identifier(db_name)
                        )
                    )
                    
                    logger.info(f"Dropped database: {db_name}")
                    return True, f"Database {db_name} dropped successfully"
                    
        except psycopg.Error as e:
            error_msg = f"Failed to drop database: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    @classmethod
    def get_database_info(cls, db_name: str) -> Optional[dict[str, Any]]:
        """
        Return basic metadata for a PostgreSQL database.

        - Single SQL roundtrip using pg_catalog.
        - Works without superuser; `connections` may be partial if the role
          lacks `pg_read_all_stats`.
        - Returns: None if the db doesn't exist.
        """
        if not db_name or not cls.database_exists(db_name):
            return None

        SQL = """
        SELECT
            d.datname,
            d.datcollate AS collation,
            pg_encoding_to_char(d.encoding) AS encoding,
            pg_database_size(d.oid) AS size_bytes,
            r.rolname AS owner,
            COALESCE(sa.conn_count, 0) AS connections
        FROM pg_database AS d
        JOIN pg_roles AS r ON r.oid = d.datdba
        LEFT JOIN LATERAL (
            SELECT count(*)::int AS conn_count
            FROM pg_stat_activity
            WHERE datname = d.datname
        ) sa ON TRUE
        WHERE d.datname = %(dbname)s
        """

        def _fmt_bytes(n: int) -> str:
            # Binary units (KiB, MiB, GiB) with simple thresholds
            if n < 1024:
                return f"{n} B"
            if n < 1024**2:
                return f"{n/1024:.1f} KB"
            if n < 1024**3:
                return f"{n/1024**2:.1f} MB"
            return f"{n/1024**3:.2f} GB"

        try:
            # Use the maintenance DB to query catalogs about other DBs
            conn_params = cls.get_connection_params("postgres")

            # Optional: enforce quick fail and safe session defaults if supported
            # conn_params.setdefault("options",
            #     "-c statement_timeout=5000 -c idle_in_transaction_session_timeout=5000 -c search_path=pg_catalog"
            # )

            with psycopg.connect(**conn_params) as conn:
                conn.read_only = True  # psycopg3 feature; we're only reading
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(SQL, {"dbname": db_name})
                    row = cur.fetchone()
                    if not row:
                        return None

                    info = dict(row)
                    size_bytes = int(info.get("size_bytes", 0))
                    info["size_human"] = _fmt_bytes(size_bytes)

                    # If you want details per schema, keep this delegated (it likely uses db_name)
                    info["schemas"] = cls.get_schema_info(db_name)

                    return info

        except psycopg.Error as e:
            logger.error("Error getting database info: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error getting database info: %s", e)
            return None
    
    @classmethod
    def get_schema_info(cls, db_name: str) -> Dict[str, Any]:
        """
        Get schema information using psycopg3
        
        Args:
            db_name: Database name
            
        Returns:
            Dictionary with schema info
        """
        try:
            with psycopg.connect(
                **cls.get_connection_params(db_name)
            ) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT 
                            s.schema_name,
                            COUNT(DISTINCT t.table_name) as table_count,
                            COUNT(DISTINCT v.table_name) as view_count,
                            pg_size_pretty(
                                COALESCE(SUM(pg_total_relation_size(
                                    quote_ident(t.table_schema)||'.'||quote_ident(t.table_name)
                                )::bigint), 0)
                            ) as total_size
                        FROM information_schema.schemata s
                        LEFT JOIN information_schema.tables t 
                            ON s.schema_name = t.table_schema
                            AND t.table_type = 'BASE TABLE'
                        LEFT JOIN information_schema.views v
                            ON s.schema_name = v.table_schema
                        WHERE s.schema_name NOT IN (
                            'pg_catalog', 'information_schema', 'pg_toast'
                        )
                        GROUP BY s.schema_name
                        ORDER BY s.schema_name
                        """
                    )
                    
                    schemas = {}
                    for row in cur.fetchall():
                        schemas[row['schema_name']] = {
                            'table_count': row['table_count'] or 0,
                            'view_count': row['view_count'] or 0,
                            'total_size': row['total_size'] or '0 bytes'
                        }
                    
                    return schemas
                    
        except psycopg.Error as e:
            logger.error(f"Error getting schema info: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting schema info: {e}")
            return {}
    
    @classmethod
    def test_connection(cls, db_name: str) -> Tuple[bool, str]:
        """
        Test database connection using psycopg3
        
        Args:
            db_name: Database name to test
            
        Returns:
            Tuple of (success, message)
        """
        try:
            with psycopg.connect(
                **cls.get_connection_params(db_name),
                connect_timeout=5
            ) as conn:
                with conn.cursor() as cur:
                    # Test query
                    cur.execute("SELECT version()")
                    result = cur.fetchone()
                    if result is None:
                        return False, "No version information returned from database"
                    version = result[0]
                    return True, f"Connected successfully. PostgreSQL {version}"
                    
        except InvalidCatalogName:
            return False, f"Database '{db_name}' does not exist"
        except psycopg.OperationalError as e:
            return False, f"Cannot connect to database: {e}"
        except psycopg.Error as e:
            return False, f"Database error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"