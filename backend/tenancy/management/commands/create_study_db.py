# backend/tenancy/management/commands/create_study_db.py
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.conf import settings
from backend.tenancy.models import Study
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class Command(BaseCommand):
    help = 'Create database for a study'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'study_code',
            type=str,
            help='Study code (e.g., TEST001)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Drop existing database if it exists',
        )
    
    def handle(self, *args, **options):
        study_code = options['study_code']
        force = options.get('force', False)
        
        try:
            # Get study
            study = Study.objects.get(code=study_code)
            
            # Connect to PostgreSQL server (not specific database)
            conn = psycopg2.connect(
                host=settings.STUDY_DB_HOST,
                port=settings.STUDY_DB_PORT,
                user=settings.STUDY_DB_USER,
                password=settings.STUDY_DB_PASSWORD,
                database='postgres'  # Connect to default postgres DB
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (study.db_name,)
            )
            exists = cursor.fetchone() is not None
            
            if exists and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'Database {study.db_name} already exists. '
                        'Use --force to drop and recreate.'
                    )
                )
                return
            
            if exists and force:
                # Terminate connections to the database
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                      AND pid <> pg_backend_pid()
                """, (study.db_name,))
                
                # Drop database
                cursor.execute(f'DROP DATABASE IF EXISTS "{study.db_name}"')
                self.stdout.write(
                    self.style.WARNING(f'Dropped existing database {study.db_name}')
                )
            
            # Create database
            cursor.execute(f"""
                CREATE DATABASE "{study.db_name}"
                WITH ENCODING='UTF8' 
                TEMPLATE=template0
                LC_COLLATE='en_US.UTF-8'
                LC_CTYPE='en_US.UTF-8';
            """)
            
            self.stdout.write(
                self.style.SUCCESS(f'Created database {study.db_name}')
            )
            
            # Connect to new database and create schema
            cursor.close()
            conn.close()
            
            # Connect to the new database
            conn = psycopg2.connect(
                host=settings.STUDY_DB_HOST,
                port=settings.STUDY_DB_PORT,
                user=settings.STUDY_DB_USER,
                password=settings.STUDY_DB_PASSWORD,
                database=study.db_name
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Create schemas
            cursor.execute("CREATE SCHEMA IF NOT EXISTS data;")
            cursor.execute("CREATE SCHEMA IF NOT EXISTS public;")
            
            # Grant permissions
            cursor.execute(f"""
                GRANT ALL ON SCHEMA data TO {settings.STUDY_DB_USER};
                GRANT ALL ON SCHEMA public TO {settings.STUDY_DB_USER};
                ALTER DATABASE "{study.db_name}" SET search_path TO data, public;
            """)
            
            self.stdout.write(
                self.style.SUCCESS('Created schemas and set permissions')
            )
            
            # Close connections
            cursor.close()
            conn.close()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully created database for study {study_code}!'
                )
            )
            self.stdout.write(
                '\nNext steps:\n'
                '1. Run migrations for study database:\n'
                f'   python manage.py migrate --database={study.db_name}\n'
                '2. Create study-specific models in backend/studies/{study.code.lower()}/\n'
            )
            
        except Study.DoesNotExist:
            raise CommandError(f'Study with code "{study_code}" does not exist')
        except psycopg2.Error as e:
            raise CommandError(f'Database error: {e}')
        except Exception as e:
            raise CommandError(f'Error: {e}')