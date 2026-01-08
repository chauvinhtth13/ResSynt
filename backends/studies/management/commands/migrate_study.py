# backend/studies/management/commands/migrate_study.py
"""
Smart migrate command for study apps - Auto-detect database.

Usage:
    python manage.py migrate_study 43EN              # Migrate study_43en to db_study_43en
    python manage.py migrate_study 43en --fake       # Mark as applied without running
    python manage.py migrate_study 43EN --make       # Make migrations only
    python manage.py migrate_study 43EN --show       # Show migration status only
    python manage.py migrate_study 43EN --all        # Make + Show + Migrate (default)
    
This command automatically routes study apps to their correct databases.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections


class Command(BaseCommand):
    help = 'Smart migrate for study apps - auto-detects database'

    def add_arguments(self, parser):
        parser.add_argument(
            'study_code',
            type=str,
            help='Study code (e.g., 43EN or 43en)'
        )
        parser.add_argument(
            '--fake',
            action='store_true',
            help='Mark migrations as applied without running them'
        )
        parser.add_argument(
            '--fake-initial',
            action='store_true',
            help='Detect if tables already exist and fake-apply initial migrations'
        )
        parser.add_argument(
            '--make',
            action='store_true',
            help='Only make migrations (do not apply)'
        )
        parser.add_argument(
            '--show',
            action='store_true',
            help='Only show migration status'
        )
        parser.add_argument(
            '--skip-make',
            action='store_true',
            help='Skip makemigrations step'
        )
        parser.add_argument(
            'migration_name',
            nargs='?',
            help='Target migration name (optional)'
        )

    def handle(self, *args, **options):
        # Normalize study code
        study_code = options['study_code'].upper()
        study_code_lower = study_code.lower()
        
        # Auto-generate app_label and db_name
        app_label = f"study_{study_code_lower}"
        db_name = f"db_study_{study_code_lower}"
        
        # Options
        fake = options.get('fake', False)
        fake_initial = options.get('fake_initial', False)
        make_only = options.get('make', False)
        show_only = options.get('show', False)
        skip_make = options.get('skip_make', False)
        migration_name = options.get('migration_name')
        
        # Header
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f" MIGRATE STUDY: {study_code}"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"  App Label:  {app_label}")
        self.stdout.write(f"  Database:   {db_name}")
        self.stdout.write("=" * 60 + "\n")
        
        # Check database exists
        if db_name not in connections.databases:
            raise CommandError(
                f"Database '{db_name}' is not configured.\n"
                f"Make sure the study '{study_code}' exists and database is registered."
            )
        
        # Test database connection
        try:
            conn = connections[db_name]
            conn.ensure_connection()
            self.stdout.write(self.style.SUCCESS(f"✓ Database connection OK\n"))
        except Exception as e:
            raise CommandError(f"Cannot connect to database '{db_name}': {e}")
        
        # Show only mode
        if show_only:
            self.stdout.write("Migration status:")
            call_command('showmigrations', app_label, database=db_name)
            return
        
        # Make migrations
        if not skip_make:
            self.stdout.write("Step 1: Creating migrations...")
            try:
                call_command('makemigrations', app_label, verbosity=1)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  makemigrations: {e}"))
        
        if make_only:
            self.stdout.write(self.style.SUCCESS("\n✓ Makemigrations completed (--make flag)"))
            return
        
        # Show migration plan
        self.stdout.write("\nStep 2: Migration plan:")
        call_command('showmigrations', app_label, database=db_name)
        
        # Run migrations
        self.stdout.write("\nStep 3: Applying migrations...")
        
        migrate_kwargs = {
            'database': db_name,
            'verbosity': 1,
        }
        
        if migration_name:
            migrate_kwargs['migration_name'] = migration_name
            
        if fake:
            migrate_kwargs['fake'] = True
            self.stdout.write(self.style.WARNING("  (fake mode - marking as applied)"))
        elif fake_initial:
            migrate_kwargs['fake_initial'] = True
            self.stdout.write(self.style.WARNING("  (fake-initial mode)"))
        
        try:
            call_command('migrate', app_label, **migrate_kwargs)
            self.stdout.write(self.style.SUCCESS("\n✓ Migrations completed successfully!"))
        except Exception as e:
            raise CommandError(f"Migration failed: {e}")
        
        self.stdout.write("=" * 60 + "\n")
