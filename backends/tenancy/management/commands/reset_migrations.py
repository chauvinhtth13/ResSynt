# backends/tenancy/management/commands/reset_migrations.py
"""
Command: python manage.py reset_migrations

Xóa tất cả records trong bảng django_migrations để reset migrations.
"""
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Reset all migration records from django_migrations table'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompt',
        )
    
    def handle(self, *args, **options):
        if not options['confirm']:
            confirm = input(
                "\n⚠️  WARNING: This will delete ALL migration records from django_migrations table.\n"
                "   You will need to run 'makemigrations' and 'migrate' after this.\n"
                "   Continue? [yes/no]: "
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('❌ Operation cancelled.'))
                return
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'django_migrations'
                );
            """)
            exists = cursor.fetchone()[0]
            
            if not exists:
                self.stdout.write(self.style.WARNING('⚠️  Table django_migrations does not exist yet.'))
                return
            
            # Count before delete
            cursor.execute("SELECT COUNT(*) FROM django_migrations;")
            count = cursor.fetchone()[0]
            
            if count == 0:
                self.stdout.write(self.style.SUCCESS('✅ No migration records to delete.'))
                return
            
            # Delete all records
            cursor.execute("DELETE FROM django_migrations;")
            
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {count} migration records.'))
            self.stdout.write(self.style.SUCCESS('\nNext steps:'))
            self.stdout.write('  1. python manage.py makemigrations')
            self.stdout.write('  2. python manage.py migrate --fake-initial')
