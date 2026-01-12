# backends/audit_logs/management/commands/setup_audit_schema.py
"""
Management command to setup 'logs' schema in study databases.

This command should be run BEFORE running migrations for study apps
to ensure the 'logs' schema exists.

Usage:
    python manage.py setup_audit_schema --database db_study_43en
    python manage.py setup_audit_schema --all-studies
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup logs schema in study databases for audit log tables'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            help='Specific study database alias (e.g., db_study_43en)',
        )
        parser.add_argument(
            '--all-studies',
            action='store_true',
            help='Setup schema for all study databases',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be executed without making changes',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if options['all_studies']:
            databases = self._get_all_study_databases()
        elif options['database']:
            databases = [options['database']]
        else:
            raise CommandError(
                'You must specify either --database or --all-studies'
            )
        
        if not databases:
            self.stdout.write(
                self.style.WARNING('No study databases found.')
            )
            return
        
        for db_alias in databases:
            self._setup_schema(db_alias, dry_run)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'{"[DRY RUN] " if dry_run else ""}Schema setup completed for {len(databases)} database(s).'
            )
        )
    
    def _get_all_study_databases(self):
        """Get all study database aliases from settings."""
        study_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        databases = []
        
        for db_alias in connections.databases.keys():
            if db_alias.startswith(study_prefix):
                databases.append(db_alias)
        
        return databases
    
    def _setup_schema(self, db_alias, dry_run=False):
        """Setup logs schema in a specific database."""
        self.stdout.write(f'\n{"="*50}')
        self.stdout.write(f'Setting up schema for: {db_alias}')
        self.stdout.write(f'{"="*50}')
        
        # Verify database exists
        if db_alias not in connections.databases:
            self.stdout.write(
                self.style.ERROR(f'Database {db_alias} not found in settings.')
            )
            return
        
        try:
            connection = connections[db_alias]
            vendor = connection.vendor
            
            # SQL to create schemas (if not exist)
            if vendor == 'postgresql':
                create_schemas_sql = [
                    # Create 'data' schema for CRF tables
                    "CREATE SCHEMA IF NOT EXISTS data;",
                    # Create 'logging' schema for audit tables
                    "CREATE SCHEMA IF NOT EXISTS logging;",
                    # Grant permissions (adjust as needed)
                    "GRANT ALL ON SCHEMA data TO PUBLIC;",
                    "GRANT ALL ON SCHEMA logging TO PUBLIC;",
                ]
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Database vendor {vendor} may not support schemas. '
                        'Skipping schema creation.'
                    )
                )
                return
            
            if dry_run:
                self.stdout.write('[DRY RUN] Would execute:')
                for sql in create_schemas_sql:
                    self.stdout.write(f'  {sql}')
                return
            
            # Execute SQL
            with connection.cursor() as cursor:
                for sql in create_schemas_sql:
                    self.stdout.write(f'Executing: {sql}')
                    cursor.execute(sql)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Schemas created successfully in {db_alias}'
                )
            )
            
            # Verify schemas exist
            self._verify_schemas(connection)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up schema: {e}')
            )
            logger.exception(f'Schema setup error for {db_alias}')
    
    def _verify_schemas(self, connection):
        """Verify that schemas were created."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('data', 'logging')
            """)
            schemas = [row[0] for row in cursor.fetchall()]
        
        if 'data' in schemas and 'logging' in schemas:
            self.stdout.write(
                self.style.SUCCESS('  ✓ Verified: data and logging schemas exist')
            )
        else:
            missing = []
            if 'data' not in schemas:
                missing.append('data')
            if 'logging' not in schemas:
                missing.append('logging')
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Missing schemas: {missing}')
            )
