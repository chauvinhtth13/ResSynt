# backends/tenancy/management/commands/migrate_audit_log.py
"""
Migrate audit_log tables to all study databases

This command ensures audit_log tables are created in all study databases
"""
from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
from backends.tenancy.db_router import set_current_db, clear_current_db
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate audit_log tables to all study databases'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            help='Migrate only to specific database (e.g., db_study_43en)',
        )
    
    def handle(self, *args, **options):
        """Run migrations for audit_log in all study databases"""
        
        # Get study database prefix
        study_db_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        
        # Get all configured databases
        databases = connections.databases.keys()
        
        # Filter study databases
        study_databases = [
            db for db in databases 
            if db.startswith(study_db_prefix)
        ]
        
        if options.get('database'):
            # Migrate only specific database
            target_db = options['database']
            if target_db not in study_databases:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Database {target_db} is not a study database or not configured'
                    )
                )
                return
            study_databases = [target_db]
        
        if not study_databases:
            self.stdout.write(
                self.style.WARNING('⚠️ No study databases found to migrate')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🔄 Migrating audit_log to {len(study_databases)} study database(s)...\n'
            )
        )
        
        # Migrate each study database
        for db_alias in study_databases:
            self.stdout.write(f'\n📦 Processing {db_alias}...')
            
            try:
                # Set current database context
                set_current_db(db_alias)
                
                # Run migrate command for this database
                from django.core.management import call_command
                
                self.stdout.write(f'   ✓ Running migrations for audit_log...')
                call_command(
                    'migrate',
                    'audit_log',
                    database=db_alias,
                    verbosity=0,
                    interactive=False,
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ Successfully migrated {db_alias}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Error migrating {db_alias}: {e}')
                )
                logger.exception(f"Failed to migrate {db_alias}")
                
            finally:
                # Clear database context
                clear_current_db()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✨ Audit log migration complete!\n'
            )
        )
