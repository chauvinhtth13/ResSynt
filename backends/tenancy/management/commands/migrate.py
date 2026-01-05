"""
Override migrate command to automatically migrate audit_log to all study databases
"""
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import connections
from django.conf import settings
import sys


class Command(MigrateCommand):
    """
    Extended migrate command that automatically migrates audit_log 
    to all study databases after running normal migrations
    """
    
    def handle(self, *args, **options):
        # Get the target database from options
        target_database = options.get('database')
        
        # If user is migrating a specific study database, just run normal migrate
        if target_database and target_database != 'default':
            return super().handle(*args, **options)
        
        # Run normal migrate first (for default database and management apps)
        result = super().handle(*args, **options)
        
        # Only auto-migrate audit_log to study databases if:
        # 1. No specific app is specified (full migrate), OR
        # 2. audit_log app is explicitly specified
        app_label = options.get('app_label')
        
        if app_label and app_label != 'audit_log':
            # User is migrating a specific app (not audit_log), skip auto-migration
            return result
        
        # Auto-migrate audit_log to all study databases
        self._migrate_audit_log_to_study_databases(options)
        
        return result
    
    def _migrate_audit_log_to_study_databases(self, options):
        """Migrate audit_log tables to all study databases"""
        
        # Get study database prefix
        study_db_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        
        # Get all configured databases
        databases = list(connections.databases.keys())
        
        # Filter study databases
        study_databases = [
            db for db in databases 
            if db.startswith(study_db_prefix)
        ]
        
        if not study_databases:
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🔄 Auto-migrating audit_log to {len(study_databases)} study database(s)...'
            )
        )
        
        # Migrate each study database
        for db_alias in study_databases:
            try:
                # Check if migration already applied in this database
                from django.db.migrations.recorder import MigrationRecorder
                recorder = MigrationRecorder(connections[db_alias])
                applied_migrations = recorder.applied_migrations()
                
                # Check if audit_log 0001_initial already applied
                if ('audit_log', '0001_initial') in applied_migrations:
                    self.stdout.write(
                        self.style.WARNING(f'   ⏭️  {db_alias}: audit_log already migrated, skipping')
                    )
                    continue
                
                # Run migration for this database
                self.stdout.write(f'   📦 {db_alias}: Migrating audit_log...')
                
                # Create new options dict for this database
                from django.core.management import call_command
                call_command(
                    'migrate',
                    'audit_log',
                    database=db_alias,
                    verbosity=0,
                    interactive=False,
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {db_alias}: Successfully migrated')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {db_alias}: Error - {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\n✨ Audit log auto-migration complete!\n')
        )
