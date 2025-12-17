"""
Test scheduled backup task manually
"""
from django.core.management.base import BaseCommand
from backends.tenancy.tasks import scheduled_backup_all_databases


class Command(BaseCommand):
    help = 'Test scheduled backup task for all databases'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List databases without backing up',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        
        if dry_run:
            from django.db import connection
            import psycopg
            
            self.stdout.write("="*70)
            self.stdout.write("DRY RUN: Databases that will be backed up")
            self.stdout.write("="*70)
            
            db_settings = connection.settings_dict
            conninfo = (
                f"host={db_settings['HOST']} "
                f"port={db_settings['PORT']} "
                f"user={db_settings['USER']} "
                f"password={db_settings['PASSWORD']} "
                f"dbname=postgres"
            )
            
            with psycopg.connect(conninfo) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT datname 
                        FROM pg_database 
                        WHERE datistemplate = false
                          AND datname NOT IN ('postgres', 'template0', 'template1', 'test')
                        ORDER BY datname
                    """)
                    databases = [row[0] for row in cursor.fetchall()]
            
            self.stdout.write(f"\nFound {len(databases)} databases:\n")
            for i, db in enumerate(databases, 1):
                self.stdout.write(f"  {i}. {db}")
            
            self.stdout.write("\n" + "="*70)
            self.stdout.write("Run without --dry-run to execute backup")
            self.stdout.write("="*70)
            return
        
        # Run actual backup
        self.stdout.write("="*70)
        self.stdout.write("TESTING SCHEDULED BACKUP")
        self.stdout.write("="*70)
        self.stdout.write("\n⏳ Starting backup task...\n")
        
        try:
            result = scheduled_backup_all_databases()
            
            self.stdout.write("\n" + "="*70)
            self.stdout.write("BACKUP RESULTS")
            self.stdout.write("="*70)
            
            self.stdout.write(f"\nStatus: {result['status']}")
            self.stdout.write(f"Total: {result['total']}")
            self.stdout.write(f"Success: {result['success']}")
            self.stdout.write(f"Failed: {result['failed']}")
            
            self.stdout.write("\nDetails:")
            for item in result['results']:
                status_icon = "✓" if item['status'] == 'success' else "❌"
                self.stdout.write(f"\n{status_icon} {item['database']}")
                
                if item['status'] == 'success':
                    from backends.tenancy.utils.backup_manager import get_backup_manager
                    bm = get_backup_manager()
                    size_str = bm._format_size(item['size'])
                    self.stdout.write(f"  Size: {size_str}")
                    self.stdout.write(f"  Path: {item['path']}")
                else:
                    self.stdout.write(f"  Error: {item.get('error', 'Unknown')}")
            
            self.stdout.write("\n" + "="*70)
            
            if result['failed'] > 0:
                self.stdout.write(self.style.WARNING(
                    f"\n⚠️  {result['failed']} database(s) failed to backup"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\n✓ All databases backed up successfully!"
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))
            raise
