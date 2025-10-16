# backend/tenancy/management/commands/create_study_db.py
"""
Management command to create and initialize study databases
"""
import psycopg
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections
from backends.tenancy.models import Study
from config.settings import DatabaseConfig


class Command(BaseCommand):
    help = 'Create and initialize a study database'

    def add_arguments(self, parser):
        parser.add_argument(
            'study_code',
            type=str,
            help='Study code (e.g., 43EN, 44EN)'
        )
        parser.add_argument(
            '--drop',
            action='store_true',
            help='Drop database if it exists (WARNING: destroys all data)'
        )

    def handle(self, *args, **options):
        study_code = options['study_code'].upper()
        drop_existing = options.get('drop', False)
        
        # Validate study code format
        if not study_code.replace('_', '').isalnum():
            raise CommandError(f"Invalid study code: {study_code}")
        
        # Generate database name
        db_name = f"{settings.STUDY_DB_PREFIX}{study_code.lower()}"
        
        self.stdout.write(f"Creating database: {db_name}")
        
        try:
            # Get management database config
            main_db = DatabaseConfig.get_management_db()
            
            # Connect to PostgreSQL server (not to specific database)
            conninfo = (
                f"host={main_db['HOST']} "
                f"port={main_db['PORT']} "
                f"user={main_db['USER']} "
                f"password={main_db['PASSWORD']} "
                f"dbname=postgres"  # Connect to postgres database to create new DB
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # Check if database exists
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (db_name,)
                    )
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        if drop_existing:
                            self.stdout.write(
                                self.style.WARNING(f"Dropping existing database: {db_name}")
                            )
                            # Terminate existing connections
                            cursor.execute(f"""
                                SELECT pg_terminate_backend(pid)
                                FROM pg_stat_activity
                                WHERE datname = %s AND pid <> pg_backend_pid()
                            """, (db_name,))
                            
                            cursor.execute(f'DROP DATABASE "{db_name}"')
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"Database {db_name} already exists. Use --drop to recreate.")
                            )
                            return
                    
                    # Create database
                    cursor.execute(f'CREATE DATABASE "{db_name}"')
                    self.stdout.write(
                        self.style.SUCCESS(f"Database {db_name} created")
                    )
            
            # Connect to the new database to create schema
            conninfo = (
                f"host={main_db['HOST']} "
                f"port={main_db['PORT']} "
                f"user={main_db['USER']} "
                f"password={main_db['PASSWORD']} "
                f"dbname={db_name}"
            )
            
            with psycopg.connect(conninfo, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # Create data schema
                    cursor.execute('CREATE SCHEMA IF NOT EXISTS data')
                    cursor.execute('GRANT ALL ON SCHEMA data TO CURRENT_USER')
                    self.stdout.write(
                        self.style.SUCCESS(f"Schema 'data' created")
                    )
                    
                    # Set default search path
                    cursor.execute('ALTER DATABASE "{}" SET search_path TO data, public'.format(db_name))
                    self.stdout.write(
                        self.style.SUCCESS(f"Search path configured")
                    )
            
            # Add to Django connections
            from backends.tenancy.db_loader import study_db_manager
            study_db_manager.add_study_db(db_name)
            
            self.stdout.write(
                self.style.SUCCESS(f"Database registered with Django")
            )
            
            # Run migrations
            self.stdout.write("\nRunning migrations...")
            from django.core.management import call_command
            
            # Get the study app name
            study_app = f"study_{study_code.lower()}"
            
            try:
                call_command('migrate', f'backends.studies.{study_app}', database=db_name, verbosity=1)
                self.stdout.write(
                    self.style.SUCCESS(f"Migrations completed")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Migration warning: {e}")
                )
            
            # Create or update Study record
            self.stdout.write("\nCreating Study record...")
            study, created = Study.objects.get_or_create(
                code=study_code,
                defaults={
                    'db_name': db_name,
                    'status': Study.Status.PLANNING,
                }
            )
            
            if created:
                # Set translatable name
                study.set_current_language('vi')
                study.name = f"Study {study_code}"
                study.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"Study record created: {study.code}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Study record already exists: {study.code}")
                )
            
            self.stdout.write(
                self.style.SUCCESS(f"\nStudy database {db_name} is ready!")
            )
            self.stdout.write(
                f"\nNext steps:"
            )
            self.stdout.write(
                f"1. Create study-specific models in backend/studies/{study_app}/models/"
            )
            self.stdout.write(
                f"2. Run: python manage.py makemigrations {study_app}"
            )
            self.stdout.write(
                f"3. Run: python manage.py migrate {study_app} --database={db_name}"
            )
            
        except psycopg.Error as e:
            raise CommandError(f"Database error: {e}")
        except Exception as e:
            raise CommandError(f"Error: {e}")