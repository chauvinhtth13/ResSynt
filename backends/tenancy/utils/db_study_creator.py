# backend/tenancy/utils/db_study_creator.py - COMPLETE
"""
Database creation utilities for study databases
"""
import psycopg
from psycopg import sql
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DatabaseStudyCreator:
    """Utilities for creating and managing study databases"""
    
    @classmethod
    def database_exists(cls, db_name: str) -> bool:
        """
        Check if a PostgreSQL database exists
        
        Args:
            db_name: Database name to check
            
        Returns:
            True if database exists, False otherwise
        """
        try:
            # Get connection info from settings
            from django.db import connections
            
            if 'default' not in connections.databases:
                logger.error("Default database not configured")
                return False
            
            default_db = connections.databases['default']
            
            # Connect to postgres database to check if target exists
            conninfo = (
                f"host={default_db['HOST']} "
                f"port={default_db['PORT']} "
                f"user={default_db['USER']} "
                f"password={default_db['PASSWORD']} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (db_name,)
                    )
                    exists = cursor.fetchone() is not None
                    return exists
                    
        except Exception as e:
            logger.error(f"Error checking database existence for {db_name}: {e}")
            return False
    
    @classmethod
    def create_study_database(cls, db_name: str) -> tuple[bool, str]:
        """
        Create a new study database with 'data' schema
        
        Args:
            db_name: Database name to create
            
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            # Validate database name
            if not db_name.startswith(settings.STUDY_DB_PREFIX):
                return False, f"Database name must start with '{settings.STUDY_DB_PREFIX}'"
            
            # Check if already exists
            if cls.database_exists(db_name):
                return True, f"Database '{db_name}' already exists"
            
            # Get connection info
            from django.db import connections
            default_db = connections.databases['default']
            
            # Connect to postgres database
            conninfo = (
                f"host={default_db['HOST']} "
                f"port={default_db['PORT']} "
                f"user={default_db['USER']} "
                f"password={default_db['PASSWORD']} "
                f"dbname=postgres"
            )
            
            # Create database
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(db_name)
                        )
                    )
                    logger.debug(f"Created database: {db_name}")
                    logger.debug(f"Created database: {db_name}")
            
            # Connect to new database and create 'data' schema
            conninfo_new = conninfo.replace("dbname=postgres", f"dbname={db_name}")
            
            with psycopg.connect(conninfo_new, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # Create 'data', 'audit_log', and 'management' schemas if they don't exist (creator automatically has all privileges)
                    cursor.execute("""
                        CREATE SCHEMA IF NOT EXISTS data;
                        CREATE SCHEMA IF NOT EXISTS audit_log;
                    """)
                    # Explicitly grant all privileges (redundant but harmless)
                    cursor.execute("GRANT ALL ON SCHEMA data, audit_log TO CURRENT_USER")
                    logger.debug(f"Ensured 'data', 'audit_log' schemas exist in {db_name}")
            
            return True, f"Database '{db_name}' created successfully"
            
        except psycopg.errors.DuplicateDatabase:
            return True, f"Database '{db_name}' already exists"
        except Exception as e:
            error_msg = f"Error creating database '{db_name}': {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @classmethod
    def drop_study_database(cls, db_name: str, force: bool = False) -> tuple[bool, str]:
        """
        Drop a study database (DANGEROUS!)
        
        Args:
            db_name: Database name to drop
            force: If True, force drop even with active connections
            
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            # Safety check
            if not db_name.startswith(settings.STUDY_DB_PREFIX):
                return False, f"Can only drop databases starting with '{settings.STUDY_DB_PREFIX}'"
            
            # Check if exists
            if not cls.database_exists(db_name):
                return True, f"Database '{db_name}' does not exist"
            
            # Get connection info
            from django.db import connections
            default_db = connections.databases['default']
            
            # Connect to postgres database
            conninfo = (
                f"host={default_db['HOST']} "
                f"port={default_db['PORT']} "
                f"user={default_db['USER']} "
                f"password={default_db['PASSWORD']} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    if force:
                        # Terminate all connections first
                        cursor.execute(
                            """
                            SELECT pg_terminate_backend(pg_stat_activity.pid)
                            FROM pg_stat_activity
                            WHERE pg_stat_activity.datname = %s
                            AND pid <> pg_backend_pid()
                            """,
                            (db_name,)
                        )
                    
                    cursor.execute(
                        sql.SQL("DROP DATABASE {}").format(
                            sql.Identifier(db_name)
                        )
                    )
                    logger.warning(f"Dropped database: {db_name}")
                    logger.warning(f"Dropped database: {db_name}")
            
            return True, f"Database '{db_name}' dropped successfully"
            
        except Exception as e:
            error_msg = f"Error dropping database '{db_name}': {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @classmethod
    def list_study_databases(cls) -> list[str]:
        """
        List all study databases
        
        Returns:
            List of study database names
        """
        try:
            from django.db import connections
            default_db = connections.databases['default']
            
            conninfo = (
                f"host={default_db['HOST']} "
                f"port={default_db['PORT']} "
                f"user={default_db['USER']} "
                f"password={default_db['PASSWORD']} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT datname FROM pg_database WHERE datname LIKE %s ORDER BY datname",
                        (f"{settings.STUDY_DB_PREFIX}%",)
                    )
                    databases = [row[0] for row in cursor.fetchall()]
                    return databases
                    
        except Exception as e:
            logger.error(f"Error listing study databases: {e}")
            return []
    
    @classmethod
    def get_database_info(cls, db_name: str) -> dict:
        """
        Get information about a database
        
        Args:
            db_name: Database name
            
        Returns:
            Dictionary with database information
        """
        try:
            from django.db import connections
            default_db = connections.databases['default']
            
            conninfo = (
                f"host={default_db['HOST']} "
                f"port={default_db['PORT']} "
                f"user={default_db['USER']} "
                f"password={default_db['PASSWORD']} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo) as conn:
                with conn.cursor() as cursor:
                    # Get database info
                    cursor.execute(
                        """
                        SELECT 
                            pg_database.datname,
                            pg_size_pretty(pg_database_size(pg_database.datname)) as size,
                            pg_encoding_to_char(pg_database.encoding) as encoding,
                            pg_database.datcollate as collate
                        FROM pg_database
                        WHERE datname = %s
                        """,
                        (db_name,)
                    )
                    
                    row = cursor.fetchone()
                    if not row:
                        return {'exists': False}
                    
                    return {
                        'exists': True,
                        'name': row[0],
                        'size': row[1],
                        'encoding': row[2],
                        'collate': row[3],
                    }
                    
        except Exception as e:
            logger.error(f"Error getting database info for {db_name}: {e}")
            return {'exists': False, 'error': str(e)}