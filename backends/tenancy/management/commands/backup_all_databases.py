"""
Management command to backup ALL databases with asymmetric encryption
Automatically discovers and backups all study databases
"""
import getpass
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from backends.tenancy.models import User, ServerKey, EncryptionAuditLog
from backends.tenancy.utils.backup_manager import BackupManager
from backends.tenancy.utils.asymmetric_encryption import AsymmetricBackupEncryption


class Command(BaseCommand):
    help = 'Backup ALL databases with asymmetric encryption'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='system_backup',
            help='Username to sign backups (default: system_backup)'
        )
        parser.add_argument(
            '--schemas',
            type=str,
            nargs='*',
            help='Schema names to backup from each database (default: all). Example: --schemas data log'
        )
        parser.add_argument(
            '--exclude',
            type=str,
            nargs='*',
            default=['template0', 'template1', 'postgres'],
            help='Databases to exclude (default: template0 template1 postgres)'
        )
        parser.add_argument(
            '--user-password',
            type=str,
            help='User private key password (for signing)'
        )
        parser.add_argument(
            '--server-password',
            type=str,
            help='Server private key password (for encryption)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show databases that will be backed up without actually backing up'
        )
    
    def handle(self, *args, **options):
        username = options['user']
        schemas = options.get('schemas')
        exclude = options.get('exclude', [])
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('BACKUP ALL DATABASES WITH ASYMMETRIC ENCRYPTION'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Validate user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f'User "{username}" does not exist.\n'
                f'Create system backup user first:\n'
                f'  python manage.py generate_user_key system_backup'
            )
        
        # Check if user has RSA key
        if not user.public_key_pem:
            raise CommandError(
                f'User "{username}" does not have RSA key.\n'
                f'Generate key first:\n'
                f'  python manage.py generate_user_key {username}'
            )
        
        # Check server key
        server_key = ServerKey.get_active_key()
        if not server_key:
            raise CommandError(
                'No active server key found.\n'
                'Generate server key first:\n'
                '  python manage.py generate_server_keys'
            )
        
        # Get list of all databases
        databases = self._get_all_databases(exclude)
        
        if not databases:
            self.stdout.write(self.style.WARNING('No databases found to backup.'))
            return
        
        self.stdout.write(f'\n📊 Configuration:')
        self.stdout.write(f'  User: {user.username} (ID: {user.id})')
        self.stdout.write(f'  Encryption: RSA-4096 + AES-256-GCM')
        self.stdout.write(f'  Server Key: {server_key.fingerprint[:16]}...')
        if schemas:
            self.stdout.write(f'  Schemas: {", ".join(schemas)}')
        else:
            self.stdout.write(f'  Schemas: ALL')
        self.stdout.write(f'\n📦 Databases to backup: {len(databases)}')
        for i, db in enumerate(databases, 1):
            self.stdout.write(f'  {i}. {db}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No backups will be created'))
            return
        
        # Get passwords
        user_password = options.get('user_password')
        server_password = options.get('server_password')
        
        if not user_password:
            self.stdout.write(f'\nEnter {username} private key password:')
            user_password = getpass.getpass('User password: ')
        
        if not server_password:
            self.stdout.write('\nEnter server private key password:')
            server_password = getpass.getpass('Server password: ')
        
        # Backup each database
        self.stdout.write(f'\n🚀 Starting backup process...\n')
        
        results = {
            'total': len(databases),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        manager = BackupManager()
        
        for i, database in enumerate(databases, 1):
            self.stdout.write(f'[{i}/{len(databases)}] Backing up {database}...')
            
            try:
                # Step 1: Create unencrypted backup
                result = manager.create_backup(
                    database=database,
                    compress=True,
                    schemas=schemas
                )
                
                if result['status'] != 'success':
                    raise Exception(f"Backup failed: {result.get('error')}")
                
                backup_path = result['path']
                self.stdout.write(f'  ✓ Created: {Path(backup_path).name} ({result.get("size", 0) / 1024 / 1024:.2f} MB)')
                
                # Step 2: Load keys (only first time)
                if i == 1:
                    self.stdout.write(f'  🔐 Loading encryption keys...')
                    
                    from backends.tenancy.utils.key_manager import UserKeyManager
                    
                    # Load user private key
                    user_private_pem = input(f'\nPaste {username} private key PEM or press Enter to load from file: ').strip()
                    
                    if not user_private_pem:
                        key_file = f'{username}_private_key.pem'
                        if not Path(key_file).exists():
                            raise CommandError(
                                f'Private key file not found: {key_file}\n'
                                f'Either paste the key or provide the file.'
                            )
                        with open(key_file, 'rb') as f:
                            user_private_pem = f.read()
                    else:
                        user_private_pem = user_private_pem.encode('utf-8')
                    
                    user_private_key = UserKeyManager.load_private_key(user_private_pem, user_password)
                    
                    # Load server keys
                    server_private_key = server_key.get_private_key(server_password)
                    server_public_key = server_key.get_public_key()
                    
                    self.stdout.write('  ✓ Keys loaded\n')
                
                # Step 3: Encrypt backup
                encrypted_path = Path(str(backup_path).replace('.backup', '_encrypted.backup'))
                
                encrypt_result = AsymmetricBackupEncryption.encrypt_file(
                    input_path=backup_path,
                    output_path=str(encrypted_path),
                    user_private_key=user_private_key,
                    server_public_key=server_public_key,
                    user_id=user.id
                )
                
                if encrypt_result['status'] != 'success':
                    raise Exception(f"Encryption failed: {encrypt_result.get('error')}")
                
                self.stdout.write(f'  ✓ Encrypted: {encrypted_path.name}')
                
                # Remove unencrypted backup
                Path(backup_path).unlink()
                
                # Rename encrypted file
                final_path = Path(backup_path)
                encrypted_path.rename(final_path)
                
                # Log to audit
                EncryptionAuditLog.log_encrypt(
                    user=user,
                    backup_file=str(final_path),
                    success=True,
                    details={
                        'database': database,
                        'schemas': schemas if schemas else 'all',
                        'size': encrypt_result.get('size'),
                        'algorithm': encrypt_result.get('algorithm')
                    }
                )
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ SUCCESS: {final_path.name}\n'))
                
                results['success'] += 1
                results['details'].append({
                    'database': database,
                    'status': 'success',
                    'path': str(final_path)
                })
                
            except Exception as e:
                # Log failed attempt
                EncryptionAuditLog.log_encrypt(
                    user=user,
                    backup_file=backup_path if 'backup_path' in locals() else '',
                    success=False,
                    details={
                        'database': database,
                        'error': str(e)
                    }
                )
                
                self.stdout.write(self.style.ERROR(f'  ❌ FAILED: {str(e)}\n'))
                results['failed'] += 1
                results['details'].append({
                    'database': database,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('BACKUP SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'\nTotal: {results["total"]}')
        self.stdout.write(self.style.SUCCESS(f'Success: {results["success"]}'))
        if results['failed'] > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {results["failed"]}'))
        
        self.stdout.write('\nDetails:')
        for detail in results['details']:
            if detail['status'] == 'success':
                self.stdout.write(self.style.SUCCESS(f'  ✓ {detail["database"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {detail["database"]}: {detail.get("error")}'))
    
    def _get_all_databases(self, exclude):
        """Get list of all databases from PostgreSQL server"""
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
                    ORDER BY datname
                """)
                for row in cursor.fetchall():
                    db_name = row[0]
                    if db_name not in exclude:
                        databases.append(db_name)
        
        return databases
