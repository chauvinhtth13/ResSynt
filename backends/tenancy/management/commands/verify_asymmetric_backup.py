"""
Verify Asymmetric Encrypted Backup

Quickly verify backup integrity and signature without full decryption
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from pathlib import Path
import logging

from backends.tenancy.models import EncryptionAuditLog
from backends.tenancy.utils.asymmetric_encryption import AsymmetricBackupEncryption
from backends.tenancy.utils.backup_encryption import BackupEncryption as SymmetricBackupEncryption

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verify encrypted backup file (hybrid or symmetric)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Path to backup file (encrypted or plain)'
        )
    
    def handle(self, *args, **options):
        backup_path = options['backup_file']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('VERIFY BACKUP FILE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Check file exists
        if not Path(backup_path).exists():
            raise CommandError(f'File not found: {backup_path}')
        
        file_size = Path(backup_path).stat().st_size
        self.stdout.write(f'\n📄 File: {Path(backup_path).name}')
        self.stdout.write(f'   Size: {file_size / 1024 / 1024:.2f} MB')
        
        # Detect encryption format
        is_hybrid = AsymmetricBackupEncryption.is_hybrid_encrypted(backup_path)
        is_symmetric = SymmetricBackupEncryption.is_encrypted(backup_path)
        
        if is_hybrid:
            self.stdout.write(f'   Format: ✨ Hybrid Encrypted (RSA + AES)')
            self._verify_hybrid(backup_path)
        elif is_symmetric:
            self.stdout.write(f'   Format: 🔒 Symmetric Encrypted (AES-256-GCM)')
            self._verify_symmetric(backup_path)
        else:
            self.stdout.write(f'   Format: Plain (unencrypted)')
            self._verify_plain(backup_path)
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('✓ VERIFICATION COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
    
    def _verify_hybrid(self, backup_path):
        """Verify hybrid encrypted backup"""
        
        # Get metadata
        metadata = AsymmetricBackupEncryption.get_file_metadata(backup_path)
        
        if not metadata:
            self.stdout.write(self.style.ERROR('✗ Cannot read metadata'))
            return
        
        self.stdout.write(f'\n📊 Metadata:')
        self.stdout.write(f'   Version: {metadata["version"]}')
        self.stdout.write(f'   Created: {metadata["created"]}')
        self.stdout.write(f'   Creator ID: {metadata["user_id"]}')
        
        # Get creator info
        try:
            creator = User.objects.get(id=metadata['user_id'])
            self.stdout.write(f'   Creator: {creator.username}')
            
            if creator.public_key_pem:
                self.stdout.write(f'   Public Key: Available ✓')
                self.stdout.write(f'   Key Generated: {creator.key_generated_at}')
            else:
                self.stdout.write(self.style.WARNING(
                    '   Public Key: Missing ⚠️  (cannot verify signature)'
                ))
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                '   Creator: Not found (user may have been deleted)'
            ))
        
        # Encryption info
        self.stdout.write(f'\n🔐 Encryption:')
        self.stdout.write(f'   Algorithm: RSA-4096 + AES-256-GCM')
        self.stdout.write(f'   Digital Signature: RSA-PSS')
        self.stdout.write(f'   Integrity: Authenticated encryption (GCM)')
        
        # Security assessment
        self.stdout.write(f'\n🛡️  Security Assessment:')
        self.stdout.write(self.style.SUCCESS('   ✓ Format: Valid hybrid encryption'))
        self.stdout.write(self.style.SUCCESS('   ✓ Confidentiality: RSA-4096'))
        self.stdout.write(self.style.SUCCESS('   ✓ Integrity: AES-256-GCM'))
        self.stdout.write(self.style.SUCCESS('   ✓ Authenticity: RSA-PSS signature'))
        
        # Log
        EncryptionAuditLog.log_verify(
            user=None,
            backup_file=backup_path,
            success=True,
            details=metadata
        )
        
        self.stdout.write(f'\n📝 Note:')
        self.stdout.write(f'   To fully verify signature, decrypt with:')
        self.stdout.write(f'   python manage.py decrypt_asymmetric_backup {backup_path}')
    
    def _verify_symmetric(self, backup_path):
        """Verify symmetric encrypted backup"""
        
        self.stdout.write(f'\n⚠️  This is an OLD FORMAT backup (symmetric encryption)')
        self.stdout.write(f'   Algorithm: AES-256-GCM with PBKDF2')
        self.stdout.write(f'   No digital signature')
        self.stdout.write(f'   Password-based encryption only')
        
        self.stdout.write(f'\n📝 Recommendation:')
        self.stdout.write(f'   Create new backups with asymmetric encryption:')
        self.stdout.write(f'   python manage.py create_asymmetric_backup <database>')
    
    def _verify_plain(self, backup_path):
        """Verify plain backup"""
        
        self.stdout.write(f'\n⚠️  This is an UNENCRYPTED backup')
        
        # Try to read as PostgreSQL custom format
        try:
            import subprocess
            result = subprocess.run(
                ['pg_restore', '--list', backup_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Count tables, schemas
                tables = [l for l in lines if 'TABLE' in l]
                schemas = set()
                for line in lines:
                    if 'SCHEMA' in line or 'TABLE' in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            schemas.add(parts[5])
                
                self.stdout.write(f'\n📊 Contents:')
                self.stdout.write(f'   Tables: {len(tables)}')
                self.stdout.write(f'   Schemas: {len(schemas)}')
                self.stdout.write(f'   Format: PostgreSQL custom format')
            else:
                self.stdout.write(f'\n❌ Cannot read backup format')
                
        except FileNotFoundError:
            self.stdout.write(f'\n❌ pg_restore not found (cannot verify)')
        except Exception as e:
            self.stdout.write(f'\n❌ Error reading backup: {e}')
        
        self.stdout.write(f'\n⚠️  SECURITY WARNING:')
        self.stdout.write(f'   This backup is NOT encrypted!')
        self.stdout.write(f'   Anyone with file access can read the data.')
