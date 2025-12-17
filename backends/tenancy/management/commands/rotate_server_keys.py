"""
Rotate Server RSA Keys

Generates new server key pair and optionally re-encrypts all backups
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import getpass
import logging

from backends.tenancy.models import ServerKey, EncryptionAuditLog
from backends.tenancy.utils.key_manager import ServerKeyManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rotate server RSA key pair'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--new-password',
            type=str,
            help='Password for new private key'
        )
        parser.add_argument(
            '--old-password',
            type=str,
            help='Password for old private key (for verification)'
        )
        parser.add_argument(
            '--key-size',
            type=int,
            default=4096,
            help='New key size (default: 4096)'
        )
        parser.add_argument(
            '--keep-old',
            action='store_true',
            help='Keep old key in database (inactive)'
        )
    
    def handle(self, *args, **options):
        key_size = options['key_size']
        keep_old = options['keep_old']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('SERVER KEY ROTATION'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Check existing key
        old_key = ServerKey.get_active_key()
        
        if not old_key:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  No active server key found\n'
                '   This will create initial server key (not rotation)\n'
            ))
            confirm = input('Continue? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled')
                return
        else:
            self.stdout.write(f'\n📊 Current Key:')
            self.stdout.write(f'   Fingerprint: {old_key.fingerprint}')
            self.stdout.write(f'   Created: {old_key.created_at}')
            self.stdout.write(f'   Key Size: {old_key.key_size} bits')
            
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  KEY ROTATION WARNING:\n'
                f'   • Old encrypted backups require old key to decrypt\n'
                f'   • Store old key securely if you need to decrypt old backups\n'
                f'   • New backups will use new key\n'
            ))
            
            confirm = input('\nContinue with rotation? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled')
                return
            
            # Verify old password
            old_password = options.get('old_password')
            if not old_password:
                self.stdout.write('\nEnter current server private key password:')
                old_password = getpass.getpass('Old password: ')
            
            try:
                old_key.get_private_key(old_password)
                self.stdout.write('✓ Old password verified')
            except Exception as e:
                raise CommandError(f'Invalid old password: {e}')
        
        # Get new password
        new_password = options.get('new_password')
        if not new_password:
            self.stdout.write('\nEnter password for NEW server private key:')
            new_password = getpass.getpass('New password: ')
            new_password_confirm = getpass.getpass('Confirm new password: ')
            
            if new_password != new_password_confirm:
                raise CommandError('Passwords do not match')
        
        if len(new_password) < 16:
            raise CommandError('Password must be at least 16 characters')
        
        # Generate new keys
        self.stdout.write(f'\n🔄 Generating new RSA-{key_size} key pair...')
        self.stdout.write('   This may take a few seconds...\n')
        
        try:
            private_key, public_key = ServerKeyManager.generate_key_pair(key_size)
            
            # Export
            private_pem = ServerKeyManager.export_private_key(private_key, new_password)
            public_pem = ServerKeyManager.export_public_key(public_key)
            
            # Get key info
            key_info = ServerKeyManager.get_key_info(public_key)
            
            self.stdout.write(self.style.SUCCESS('✓ New key pair generated'))
            self.stdout.write(f'  Key Size: {key_info["key_size"]} bits')
            self.stdout.write(f'  Fingerprint: {key_info["fingerprint"]}')
            
            # Save to database
            with transaction.atomic():
                # Deactivate old key
                if old_key:
                    old_key.deactivate()
                    self.stdout.write(f'\n✓ Old key deactivated')
                
                # Create new key
                new_key = ServerKey.objects.create(
                    private_key_pem=private_pem.decode('utf-8'),
                    public_key_pem=public_pem.decode('utf-8'),
                    key_size=key_info['key_size'],
                    fingerprint=key_info['fingerprint'],
                    is_active=True,
                    rotated_from=old_key,
                    notes=f'Rotated from {old_key.fingerprint if old_key else "initial"}')
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ New key saved to database\n'
                    f'  ID: {new_key.id}\n'
                    f'  Status: ACTIVE'
                ))
                
                # Log rotation
                EncryptionAuditLog.log_key_rotation(
                    user=None,
                    details={
                        'old_fingerprint': old_key.fingerprint if old_key else None,
                        'new_fingerprint': key_info['fingerprint'],
                        'key_size': key_size
                    }
                )
                
                # Delete old key if not keeping
                if old_key and not keep_old:
                    old_fingerprint = old_key.fingerprint
                    old_key.delete()
                    self.stdout.write(f'✓ Old key deleted from database')
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  Old backups cannot be decrypted without old key!\n'
                        f'  Old key fingerprint: {old_fingerprint}'
                    ))
            
            # Instructions
            self.stdout.write(self.style.WARNING(
                f'\n📝 POST-ROTATION STEPS:\n'
                f'  1. Update .env with new password:\n'
                f'     SERVER_KEY_PASSWORD="{new_password}"\n'
                f'  2. Restart application to use new key\n'
                f'  3. New backups will use new key automatically\n'
                f'  4. Old backups require old key to decrypt\n'
            ))
            
            if old_key and keep_old:
                self.stdout.write(f'\n💾 Old key preserved in database (ID: {old_key.id})')
                self.stdout.write(f'   To decrypt old backups, you\'ll need the old password')
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ KEY ROTATION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            logger.error(f'Key rotation failed: {e}', exc_info=True)
            raise CommandError(str(e))
