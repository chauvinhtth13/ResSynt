# backend/tenancy/management/commands/migrate_study.py
"""
Management command to migrate a specific study
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Migrate a specific study app to its database'

    def add_arguments(self, parser):
        parser.add_argument(
            'study_code',
            type=str,
            help='Study code (e.g., 43EN)'
        )
        parser.add_argument(
            '--fake',
            action='store_true',
            help='Mark migrations as applied without running them'
        )

    def handle(self, *args, **options):
        study_code = options['study_code'].upper()
        fake = options.get('fake', False)
        
        app_label = f"study_{study_code.lower()}"
        db_name = f"db_study_{study_code.lower()}"
        
        self.stdout.write(f"=== Migrating Study {study_code} ===")
        self.stdout.write(f"App: {app_label}")
        self.stdout.write(f"Database: {db_name}\n")
        
        # Step 1: Make migrations
        self.stdout.write("Step 1: Creating migrations...")
        call_command('makemigrations', app_label)
        
        # Step 2: Show plan
        self.stdout.write("\nStep 2: Migration plan:")
        call_command('showmigrations', app_label, database=db_name)
        
        # Step 3: Migrate
        self.stdout.write("\nStep 3: Running migrations...")
        
        if fake:
            call_command('migrate', app_label, database=db_name, fake=True)
            self.stdout.write(self.style.WARNING("Migrations marked as applied (fake)"))
        else:
            call_command('migrate', app_label, database=db_name)
            self.stdout.write(self.style.SUCCESS("Migrations applied"))