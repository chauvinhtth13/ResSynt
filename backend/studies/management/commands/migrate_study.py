# backend/studies/management/commands/migrate_study.py
"""
Management command to handle study database migrations
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections, connection
from django.conf import settings
from backend.tenancy.models import Study
from backend.tenancy.db_loader import add_study_db
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage migrations for study-specific databases'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--study',
            type=str,
            help='Study code (e.g., 43EN)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Migrate all active studies'
        )
        parser.add_argument(
            '--create-db',
            action='store_true',
            help='Create database if it does not exist'
        )
        parser.add_argument(
            '--fake',
            action='store_true',
            help='Mark migrations as run without actually running them'
        )
        parser.add_argument(
            '--fake-initial',
            action='store_true',
            help='Fake initial migration'
        )
        parser.add_argument(
            '--plan',
            action='store_true',
            help='Show migration plan without executing'
        )
    
    def handle(self, *args, **options):
        if options['all']:
            self.migrate_all_studies(options)
        elif options['study']:
            self.migrate_single_study(options['study'], options)
        else:
            raise CommandError('Please specify --study=CODE or --all')
    
    def migrate_single_study(self, study_code, options):
        """Migrate a single study database"""
        try:
            # Get study from database
            study = Study.objects.get(code__iexact=study_code)
            
            self.stdout.write(f'\n{"="*50}')
            self.stdout.write(f'Study: {study.code}')
            self.stdout.write(f'Database: {study.db_name}')
            self.stdout.write(f'{"="*50}')
            
            # Create database if requested
            if options['create_db']:
                self.create_database_if_not_exists(study.db_name)
            
            # Add study database configuration
            add_study_db(study.db_name)
            
            # Determine app name
            app_name = f'study_{study.code.lower()}'
            
            # Show plan if requested
            if options['plan']:
                self.stdout.write('\nMigration plan:')
                call_command(
                    'showmigrations',
                    app_name,
                    database=study.db_name,
                    verbosity=2
                )
                return
            
            # Build migration command arguments
            migrate_args = {
                'app_label': app_name,
                'database': study.db_name,
                'verbosity': 2,
            }
            
            if options['fake']:
                migrate_args['fake'] = True
                
            if options['fake_initial']:
                migrate_args['fake_initial'] = True
            
            # Run migration
            self.stdout.write(f'\nRunning migrations for {app_name} on {study.db_name}...')
            call_command('migrate', **migrate_args)
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully migrated {study.code}')
            )
            
        except Study.DoesNotExist:
            raise CommandError(f'Study {study_code} not found')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Error migrating {study_code}: {e}')
            )
            raise
    
    def migrate_all_studies(self, options):
        """Migrate all active study databases"""
        studies = Study.objects.filter(status=Study.Status.ACTIVE)
        
        if not studies.exists():
            self.stdout.write(self.style.WARNING('No active studies found'))
            return
        
        self.stdout.write(f'\nFound {studies.count()} active studies')
        
        success_count = 0
        failed_studies = []
        
        for study in studies:
            try:
                self.migrate_single_study(study.code, options)
                success_count += 1
            except Exception as e:
                failed_studies.append((study.code, str(e)))
                self.stdout.write(
                    self.style.ERROR(f'Failed to migrate {study.code}: {e}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Migration Summary:')
        self.stdout.write(f'  Successful: {success_count}')
        self.stdout.write(f'  Failed: {len(failed_studies)}')
        
        if failed_studies:
            self.stdout.write('\nFailed studies:')
            for code, error in failed_studies:
                self.stdout.write(f'  - {code}: {error}')
    
    def create_database_if_not_exists(self, db_name):
        """Create PostgreSQL database if it doesn't exist"""
        from django.db import connection
        from django.conf import settings
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Get connection parameters from settings
        db_settings = settings.DATABASES['default']
        
        try:
            # Connect to PostgreSQL server (not specific database)
            conn = psycopg2.connect(
                host=db_settings['HOST'],
                port=db_settings['PORT'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                database='postgres'  # Connect to default postgres database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                [db_name]
            )
            
            if not cursor.fetchone():
                # Create database
                self.stdout.write(f'Creating database {db_name}...')
                cursor.execute(f'CREATE DATABASE {db_name}')
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Database {db_name} created')
                )
                
                # Create schema if needed
                study_conn = psycopg2.connect(
                    host=db_settings['HOST'],
                    port=db_settings['PORT'],
                    user=db_settings['USER'],
                    password=db_settings['PASSWORD'],
                    database=db_name
                )
                study_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                study_cursor = study_conn.cursor()
                
                # Create data schema
                study_cursor.execute('CREATE SCHEMA IF NOT EXISTS data')
                self.stdout.write(f'✓ Schema "data" created in {db_name}')
                
                study_cursor.close()
                study_conn.close()
            else:
                self.stdout.write(f'Database {db_name} already exists')
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            raise CommandError(f'Failed to create database: {e}')