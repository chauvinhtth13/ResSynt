"""
Decrypt Asymmetric Encrypted Backup

Decrypts backup file encrypted with hybrid RSA + AES
Verifies digital signature
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from pathlib import Path
import logging
import getpass

from backends.tenancy.models import ServerKey, EncryptionAuditLog
from backends.tenancy.utils.asymmetric_encryption import AsymmetricBackupEncryption
from backends.tenancy.utils.key_manager import KeyManager

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Decrypt asymmetric encrypted backup file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'encrypted_file',
            type=str,
            help='Path to encrypted backup file'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output path for decrypted file (default: remove .encrypted)'
        )
        parser.add_argument(
            '--server-password',
            type=str,
            help='Server private key password'
        )
        parser.add_argument(
            '--no-verify',
            action='store_true',
            help='Skip signature verification'
        )
        parser.add_argument(
            '--keep-temp',
            action='store_true',
            help='Keep decrypted file (WARNING: security risk)'
        )
    
    def handle(self, *args, **options):
        encrypted_path = options['encrypted_file']
        output_path = options.get('output')
        no_verify = options['no_verify']
        keep_temp = options['keep_temp']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('DECRYPT ASYMMETRIC BACKUP'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Check file exists
        if not Path(encrypted_path).exists():
            raise CommandError(f'File not found: {encrypted_path}')
        
        # Check if hybrid encrypted
        if not AsymmetricBackupEncryption.is_hybrid_encrypted(encrypted_path):
            raise CommandError(
                'This is not a hybrid encrypted file.\n'
                'Use: python manage.py decrypt_backup (old command for symmetric)'
            )
        
        # Get metadata
        metadata = AsymmetricBackupEncryption.get_file_metadata(encrypted_path)
        
        if metadata:
            self.stdout.write(f'\n📊 File Metadata:')
            self.stdout.write(f'  Format: {metadata["format"]} (version {metadata["version"]})')
            self.stdout.write(f'  Creator ID: {metadata["user_id"]}')
            self.stdout.write(f'  Created: {metadata["created"]}')
            
            # Get creator user
            try:
                creator = User.objects.get(id=metadata['user_id'])
                self.stdout.write(f'  Creator: {creator.username}')
            except User.DoesNotExist:
                creator = None
                self.stdout.write(f'  Creator: Unknown (user deleted)')
        
        # Get server key
        server_key = ServerKey.get_active_key()
        if not server_key:
            raise CommandError(
                'No active server key found.\n'
                'Cannot decrypt without server private key.'
            )
        
        self.stdout.write(f'\n🔑 Using server key: {server_key.fingerprint[:16]}...')
        
        # Get server password
        server_password = options.get('server_password')
        if not server_password:
            self.stdout.write('\nEnter server private key password:')
            server_password = getpass.getpass('Password: ')
        
        # Load server private key
        try:
            server_private_key = server_key.get_private_key(server_password)
            self.stdout.write('✓ Server private key loaded')
        except Exception as e:
            raise CommandError(f'Failed to load server private key: {e}')
        
        # Load user public key (for verification)
        user_public_key = None
        if not no_verify and metadata and metadata['user_id']:
            try:
                creator = User.objects.get(id=metadata['user_id'])
                if creator.public_key_pem:
                    user_public_key = KeyManager.load_public_key(
                        creator.public_key_pem.encode('utf-8')
                    )
                    self.stdout.write(f'✓ Creator public key loaded ({creator.username})')
                else:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️  Creator has no public key - signature verification disabled'
                    ))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    '⚠️  Creator not found - signature verification disabled'
                ))
        
        # Decrypt
        self.stdout.write(f'\n🔓 Decrypting backup...')
        
        try:
            result = AsymmetricBackupEncryption.decrypt_file(
                input_path=encrypted_path,
                server_private_key=server_private_key,
                user_public_key=user_public_key,
                output_path=output_path,
                verify_signature=not no_verify
            )
            
            if result['status'] != 'success':
                raise CommandError(f'Decryption failed: {result.get("error")}')
            
            # Display results
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Decryption successful:\n'
                f'  Output: {result["decrypted_path"]}\n'
                f'  Size: {result.get("size", 0) / 1024 / 1024:.2f} MB'
            ))
            
            if result.get('signature_valid') is not None:
                if result['signature_valid']:
                    self.stdout.write(self.style.SUCCESS('  ✓ Signature: VALID'))
                else:
                    self.stdout.write(self.style.ERROR('  ✗ Signature: INVALID'))
            
            # Log to audit
            if metadata:
                EncryptionAuditLog.log_decrypt(
                    user=creator if metadata else None,
                    backup_file=encrypted_path,
                    backup_creator=creator if metadata else None,
                    signature_valid=result.get('signature_valid'),
                    success=True,
                    ip_address=self._get_ip_address(),
                    details={
                        'decrypted_path': result['decrypted_path'],
                        'size': result.get('size'),
                        'timestamp': result.get('timestamp')
                    }
                )
            
            # Security warning
            if keep_temp:
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  SECURITY WARNING:\n'
                    f'  Decrypted file contains sensitive data\n'
                    f'  Delete after use: {result["decrypted_path"]}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'\n📌 Next steps:\n'
                    f'  1. Verify backup: python manage.py verify_backup {result["decrypted_path"]}\n'
                    f'  2. Restore if needed\n'
                    f'  3. DELETE decrypted file for security'
                ))
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ DECRYPTION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
            
        except Exception as e:
            # Log failed attempt
            EncryptionAuditLog.log_decrypt(
                user=None,
                backup_file=encrypted_path,
                success=False,
                details={'error': str(e)}
            )
            
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            logger.error(f'Decryption failed: {e}', exc_info=True)
            raise CommandError(str(e))
    
    def _get_ip_address(self):
        """Get local IP address"""
        try:
            import socket
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return '127.0.0.1'
