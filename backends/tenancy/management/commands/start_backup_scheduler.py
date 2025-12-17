"""
Auto Backup Scheduler - Real-time Backup Every 5 Minutes

Runs automatic encrypted backups and exports audit logs
For localhost development (without Celery worker)
"""
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from backends.tenancy.models import User, ServerKey, EncryptionAuditLog
from backends.tenancy.utils.backup_manager import BackupManager
from backends.tenancy.utils.asymmetric_encryption import AsymmetricBackupEncryption
from backends.tenancy.utils.key_manager import UserKeyManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start automatic backup scheduler (every 5 minutes)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='system_backup',
            help='Username for backup signing (default: system_backup)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Backup interval in minutes (default: 5)'
        )
        parser.add_argument(
            '--databases',
            type=str,
            nargs='*',
            help='Specific databases to backup (default: all)'
        )
        parser.add_argument(
            '--schemas',
            type=str,
            nargs='*',
            help='Specific schemas to backup (default: all)'
        )
        parser.add_argument(
            '--exclude',
            type=str,
            nargs='*',
            default=['template0', 'template1', 'postgres'],
            help='Databases to exclude (default: template0 template1 postgres)'
        )
        parser.add_argument(
            '--user-key-file',
            type=str,
            help='Path to user private key file (default: {username}_private_key.pem)'
        )
        parser.add_argument(
            '--user-password',
            type=str,
            help='User private key password (INSECURE - use .env instead)'
        )
        parser.add_argument(
            '--server-password',
            type=str,
            help='Server private key password (INSECURE - use .env instead)'
        )
    
    def handle(self, *args, **options):
        username = options['user']
        interval = options['interval']
        databases = options.get('databases')
        schemas = options.get('schemas')
        exclude = options.get('exclude', [])
        user_key_file = options.get('user_key_file')
        user_password = options.get('user_password')
        server_password = options.get('server_password')
        
        # Banner
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🔄 AUTO BACKUP SCHEDULER STARTED'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Validate user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'User "{username}" not found.\n'
                f'Create user first: python manage.py generate_user_key {username}'
            ))
            return
        
        # Check user has RSA key
        if not user.public_key_pem:
            self.stdout.write(self.style.ERROR(
                f'User "{username}" has no RSA key.\n'
                f'Generate key: python manage.py generate_user_key {username}'
            ))
            return
        
        # Check server key
        server_key = ServerKey.get_active_key()
        if not server_key:
            self.stdout.write(self.style.ERROR(
                'No active server key found.\n'
                'Generate server key: python manage.py generate_server_keys'
            ))
            return
        
        # Get passwords (prompt if not provided)
        if not user_password:
            import getpass
            self.stdout.write(f'\nEnter {username} private key password:')
            user_password = getpass.getpass('User password: ')
        
        if not server_password:
            import getpass
            self.stdout.write('\nEnter server private key password:')
            server_password = getpass.getpass('Server password: ')
        
        # Load keys once
        try:
            self.stdout.write('🔐 Loading encryption keys...')
            
            # Load user private key
            if not user_key_file:
                user_key_file = f'{username}_private_key.pem'
            
            key_path = Path(user_key_file)
            if not key_path.exists():
                self.stdout.write(self.style.ERROR(
                    f'Private key file not found: {user_key_file}\n'
                    f'Generate and save key first.'
                ))
                return
            
            with open(key_path, 'rb') as f:
                user_private_pem = f.read()
            
            user_private_key = UserKeyManager.load_private_key(user_private_pem, user_password)
            server_private_key = server_key.get_private_key(server_password)
            server_public_key = server_key.get_public_key()
            
            self.stdout.write(self.style.SUCCESS('  ✓ Keys loaded successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load keys: {e}'))
            return
        
        # Configuration summary
        self.stdout.write(f'\n📊 Configuration:')
        self.stdout.write(f'  User: {user.username} (ID: {user.id})')
        self.stdout.write(f'  Interval: Every {interval} minute(s)')
        self.stdout.write(f'  Server Key: {server_key.fingerprint[:16]}...')
        if databases:
            self.stdout.write(f'  Databases: {", ".join(databases)}')
        else:
            self.stdout.write(f'  Databases: ALL')
        if schemas:
            self.stdout.write(f'  Schemas: {", ".join(schemas)}')
        else:
            self.stdout.write(f'  Schemas: ALL')
        
        # Create scheduler
        scheduler = BackupScheduler(
            user=user,
            interval_minutes=interval,
            databases=databases,
            schemas=schemas,
            exclude=exclude,
            user_private_key=user_private_key,
            server_public_key=server_public_key,
            stdout=self.stdout
        )
        
        # Start scheduler thread
        self.stdout.write(f'\n✅ Scheduler starting...')
        self.stdout.write(f'   Next backup: {scheduler.next_backup_time()}')
        self.stdout.write(f'   Press CTRL+C to stop\n')
        
        try:
            scheduler.start()
            
            # Keep main thread alive
            while scheduler.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\n⏸️  Stopping scheduler...'))
            scheduler.stop()
            self.stdout.write(self.style.SUCCESS('✓ Scheduler stopped cleanly'))


class BackupScheduler:
    """Background thread scheduler for automatic backups"""
    
    def __init__(self, user, interval_minutes, databases, schemas, exclude,
                 user_private_key, server_public_key, stdout):
        self.user = user
        self.interval = interval_minutes * 60  # Convert to seconds
        self.databases = databases
        self.schemas = schemas
        self.exclude = exclude or []
        self.user_private_key = user_private_key
        self.server_public_key = server_public_key
        self.stdout = stdout
        
        self.is_running = False
        self.thread = None
        self.backup_count = 0
        self.success_count = 0
        self.failed_count = 0
        
        # Audit log directory
        self.audit_log_dir = Path(settings.BASE_DIR) / 'logs' / 'backup_audit'
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """Start scheduler thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop scheduler thread"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def next_backup_time(self):
        """Get next backup time"""
        from datetime import timedelta
        next_time = datetime.now() + timedelta(seconds=self.interval)
        return next_time.strftime('%Y-%m-%d %H:%M:%S')
    
    def _run(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Run backup
                self._backup_all()
                
                # Sleep until next interval
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f'Scheduler error: {e}', exc_info=True)
                time.sleep(60)  # Wait 1 minute on error
    
    def _backup_all(self):
        """Execute backup for all databases"""
        start_time = datetime.now()
        timestamp = start_time.strftime('%Y%m%d_%H%M%S')
        
        self.backup_count += 1
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'BACKUP #{self.backup_count} - {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write('=' * 70)
        
        # Get list of databases
        if self.databases:
            databases = self.databases
        else:
            databases = self._discover_databases()
        
        self.stdout.write(f'Backing up {len(databases)} database(s)...\n')
        
        results = []
        manager = BackupManager()
        
        for i, database in enumerate(databases, 1):
            self.stdout.write(f'[{i}/{len(databases)}] {database}...')
            
            try:
                # Create backup
                result = manager.create_backup(
                    database=database,
                    compress=True,
                    schemas=self.schemas
                )
                
                if result['status'] != 'success':
                    raise Exception(f"Backup failed: {result.get('error')}")
                
                backup_path = result['path']
                
                # Encrypt backup
                encrypted_path = Path(str(backup_path).replace('.backup', '_encrypted.backup'))
                
                encrypt_result = AsymmetricBackupEncryption.encrypt_file(
                    input_path=backup_path,
                    user=self.user,
                    server_public_key=self.server_public_key,
                    user_private_key=self.user_private_key,
                    output_path=str(encrypted_path)
                )
                
                if encrypt_result['status'] != 'success':
                    raise Exception(f"Encryption failed: {encrypt_result.get('error')}")
                
                # Remove unencrypted backup
                Path(backup_path).unlink()
                
                # Log to audit
                EncryptionAuditLog.log_encrypt(
                    user=self.user,
                    backup_file=str(encrypted_path),
                    success=True,
                    details={
                        'database': database,
                        'schemas': self.schemas if self.schemas else 'all',
                        'size': encrypt_result.get('size'),
                        'auto_backup': True,
                        'backup_number': self.backup_count
                    }
                )
                
                self.stdout.write(f'  SUCCESS ({result.get("size", 0) / 1024 / 1024:.2f} MB)')
                
                self.success_count += 1
                results.append({
                    'database': database,
                    'status': 'success',
                    'path': str(encrypted_path),
                    'size': encrypt_result.get('size')
                })
                
            except Exception as e:
                logger.error(f'Backup failed for {database}: {e}')
                self.stdout.write(f'  FAILED: {str(e)}')
                
                # Log failed attempt
                EncryptionAuditLog.log_encrypt(
                    user=self.user,
                    backup_file=f'failed_{database}_{timestamp}',
                    success=False,
                    details={
                        'database': database,
                        'error': str(e),
                        'auto_backup': True,
                        'backup_number': self.backup_count
                    }
                )
                
                self.failed_count += 1
                results.append({
                    'database': database,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Export audit log
        audit_file = self._export_audit_log(timestamp, results)
        if audit_file:
            self.stdout.write(f'   Audit log: {audit_file.name}')
        
        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write(f'Summary:')
        self.stdout.write(f'   Duration: {duration:.2f}s')
        self.stdout.write(f'   Success: {len([r for r in results if r["status"] == "success"])}')
        self.stdout.write(f'   Failed: {len([r for r in results if r["status"] == "failed"])}')
        self.stdout.write(f'   Total session success: {self.success_count}')
        self.stdout.write(f'   Total session failed: {self.failed_count}')
        self.stdout.write(f'   Next backup: {self.next_backup_time()}')
        self.stdout.write('-' * 70)
    
    def _discover_databases(self):
        """Discover all databases on server"""
        import psycopg
        from django.db import connection
        
        db_settings = connection.settings_dict
        conninfo = (
            f"host={db_settings['HOST']} "
            f"port={db_settings['PORT']} "
            f"user={db_settings['USER']} "
            f"password={db_settings['PASSWORD']} "
            f"dbname=postgres"
        )
        
        databases = []
        
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT datname 
                    FROM pg_database 
                    WHERE datistemplate = false
                      AND datname NOT IN ('postgres', 'template0', 'template1')
                    ORDER BY datname
                """)
                databases = [row[0] for row in cursor.fetchall()]
        
        # Filter out excluded databases
        if self.exclude:
            databases = [db for db in databases if db not in self.exclude]
        
        return databases
    
    def _export_audit_log(self, timestamp, results):
        """Export audit log to file"""
        try:
            # Get logs for this backup session
            logs = EncryptionAuditLog.objects.filter(
                user=self.user,
                details__backup_number=self.backup_count
            ).order_by('timestamp')
            
            # Create audit log file
            audit_file = self.audit_log_dir / f'backup_audit_{timestamp}.txt'
            
            with open(audit_file, 'w', encoding='utf-8') as f:
                f.write('=' * 70 + '\n')
                f.write(f'BACKUP AUDIT LOG - Session #{self.backup_count}\n')
                f.write(f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                f.write(f'User: {self.user.username} (ID: {self.user.id})\n')
                f.write('=' * 70 + '\n\n')
                
                # Summary
                f.write('SUMMARY:\n')
                f.write('-' * 70 + '\n')
                f.write(f'Total databases: {len(results)}\n')
                f.write(f'Success: {len([r for r in results if r["status"] == "success"])}\n')
                f.write(f'Failed: {len([r for r in results if r["status"] == "failed"])}\n')
                f.write('\n')
                
                # Details
                f.write('DETAILS:\n')
                f.write('-' * 70 + '\n')
                for log in logs:
                    status = 'SUCCESS' if log.success else 'FAILED'
                    f.write(f'\n[{log.timestamp.strftime("%H:%M:%S")}] {status}\n')
                    f.write(f'  Database: {log.details.get("database", "N/A")}\n')
                    f.write(f'  File: {log.backup_file}\n')
                    
                    if log.success:
                        f.write(f'  Size: {log.details.get("size", 0) / 1024 / 1024:.2f} MB\n')
                        f.write(f'  Schemas: {log.details.get("schemas", "all")}\n')
                    else:
                        f.write(f'  Error: {log.details.get("error", "Unknown")}\n')
                
                # Footer
                f.write('\n' + '=' * 70 + '\n')
                f.write(f'End of audit log\n')
                f.write('=' * 70 + '\n')
            
            return audit_file
            
        except Exception as e:
            logger.error(f'Failed to export audit log: {e}', exc_info=True)
            return None
