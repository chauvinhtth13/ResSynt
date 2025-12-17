"""
Create Manual Encrypted Backup with Asymmetric Encryption

Creates database backup with hybrid RSA + AES encryption
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from pathlib import Path
import logging
import getpass

from backends.tenancy.utils.backup_manager import BackupManager
from backends.tenancy.models import ServerKey, EncryptionAuditLog
from backends.tenancy.utils.asymmetric_encryption import AsymmetricBackupEncryption

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create encrypted database backup with asymmetric encryption'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'database',
            type=str,
            help='Database name (or "default")'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='system_backup',
            help='Username to sign backup (default: system_backup)'
        )
        parser.add_argument(
            '--schemas',
            type=str,
            nargs='*',
            help='Schema names to backup (default: all schemas). Example: --schemas data log'
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
    
    def handle(self, *args, **options):
        database = options['database']
        username = options['user']
        schemas = options.get('schemas')  # List of schema names or None
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'CREATE ENCRYPTED BACKUP: {database}'))
        if schemas:
            self.stdout.write(self.style.SUCCESS(f'SCHEMAS: {", ".join(schemas)}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
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
        
        self.stdout.write(f'\n📊 Configuration:')
        self.stdout.write(f'  Database: {database}')
        self.stdout.write(f'  User: {user.username} (ID: {user.id})')
        self.stdout.write(f'  Encryption: RSA-4096 + AES-256-GCM')
        self.stdout.write(f'  Server Key: {server_key.fingerprint[:16]}...')
        
        # Get passwords
        user_password = options.get('user_password')
        server_password = options.get('server_password')
        
        if not user_password:
            self.stdout.write(f'\nEnter {username} private key password:')
            user_password = getpass.getpass('User password: ')
        
        if not server_password:
            self.stdout.write('\nEnter server private key password:')
            server_password = getpass.getpass('Server password: ')
        
        # Create backup
        try:
            manager = BackupManager()
            
            self.stdout.write(f'\n🔄 Step 1: Creating backup...')
            
            result = manager.create_backup(
                database=database,
                compress=True,
                schemas=schemas
            )
            
            if result['status'] != 'success':
                raise CommandError(f'Backup failed: {result.get("error")}')
            
            backup_path = result['path']
            
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Backup created: {Path(backup_path).name}\n'
                f'    Size: {result.get("size_mb", 0):.2f} MB\n'
                f'    Tables: {result.get("tables", 0)}'
            ))
            
            # Load keys
            self.stdout.write(f'\n🔐 Step 2: Loading encryption keys...')
            
            try:
                # Load user private key (for signing)
                from backends.tenancy.utils.key_manager import UserKeyManager
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
                self.stdout.write('  ✓ User private key loaded')
                
                # Load server keys
                server_public_key = server_key.get_public_key()
                self.stdout.write('  ✓ Server public key loaded')
                
            except Exception as e:
                raise CommandError(f'Failed to load keys: {e}')
            
            # Encrypt
            self.stdout.write(f'\n🔐 Step 3: Encrypting backup...')
            
            encrypt_result = AsymmetricBackupEncryption.encrypt_file(
                input_path=backup_path,
                user=user,
                server_public_key=server_public_key,
                user_private_key=user_private_key,
                output_path=None  # Auto-generate
            )
            
            if encrypt_result['status'] != 'success':
                raise CommandError(f'Encryption failed: {encrypt_result.get("error")}')
            
            # Remove original
            Path(backup_path).unlink()
            self.stdout.write('  ✓ Original backup removed')
            
            # Log to audit
            EncryptionAuditLog.log_encrypt(
                user=user,
                backup_file=encrypt_result['encrypted_path'],
                success=True,
                details={
                    'database': database,
                    'schemas': schemas if schemas else 'all',
                    'size': encrypt_result.get('size'),
                    'algorithm': encrypt_result.get('algorithm'),
                    'timestamp': encrypt_result.get('timestamp')
                }
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Backup encrypted:\n'
                f'  Path: {encrypt_result["encrypted_path"]}\n'
                f'  Size: {encrypt_result.get("size", 0) / 1024 / 1024:.2f} MB\n'
                f'  Algorithm: {encrypt_result.get("algorithm")}\n'
                f'  Signed by: {user.username} (ID: {user.id})\n'
                f'  Timestamp: {encrypt_result.get("timestamp")}'
            ))
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ BACKUP COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
            
        except Exception as e:
            # Log failed attempt
            EncryptionAuditLog.log_encrypt(
                user=user if 'user' in locals() else None,
                backup_file=backup_path if 'backup_path' in locals() else '',
                success=False,
                details={
                    'database': database,
                    'error': str(e)
                }
            )
            
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            logger.error(f'Backup failed: {e}', exc_info=True)
            raise CommandError(str(e))
