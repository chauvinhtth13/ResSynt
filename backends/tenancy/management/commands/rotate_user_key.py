"""
Rotate User RSA Key

Generates new RSA key pair for user
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
import getpass
import logging

from backends.tenancy.utils.key_manager import UserKeyManager
from backends.tenancy.models import EncryptionAuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rotate user RSA key pair'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username to rotate key for'
        )
        parser.add_argument(
            '--old-password',
            type=str,
            help='Old private key password (for verification)'
        )
        parser.add_argument(
            '--new-password',
            type=str,
            help='New private key password'
        )
        parser.add_argument(
            '--key-size',
            type=int,
            default=4096,
            help='New key size (default: 4096)'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        key_size = options['key_size']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'USER KEY ROTATION: {username}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        # Check if user has key
        if not user.public_key_pem:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  User has no existing key\n'
                f'   This will create initial key (not rotation)\n'
                f'   Use: python manage.py generate_user_key {username}'
            ))
            return
        
        self.stdout.write(f'\n📊 Current Key:')
        self.stdout.write(f'   User: {user.username} (ID: {user.id})')
        self.stdout.write(f'   Generated: {user.key_generated_at}')
        self.stdout.write(f'   Last Rotated: {user.key_last_rotated or "Never"}')
        
        self.stdout.write(self.style.WARNING(
            f'\n⚠️  KEY ROTATION WARNING:\n'
            f'   • Old signatures cannot be verified with new key\n'
            f'   • Backups signed with old key need old public key\n'
            f'   • New backups will use new key for signing\n'
        ))
        
        confirm = input('\nContinue with rotation? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Operation cancelled')
            return
        
        # Get passwords
        old_password = options.get('old_password')
        new_password = options.get('new_password')
        
        if not old_password:
            self.stdout.write('\nEnter OLD private key password (for verification):')
            old_password = getpass.getpass('Old password: ')
        
        if not new_password:
            self.stdout.write('\nEnter NEW private key password:')
            new_password = getpass.getpass('New password: ')
            new_password_confirm = getpass.getpass('Confirm new password: ')
            
            if new_password != new_password_confirm:
                raise CommandError('Passwords do not match')
        
        if len(new_password) < 16:
            raise CommandError('Password must be at least 16 characters')
        
        # Verify old key (if user has private key file)
        self.stdout.write(f'\n🔍 Verifying old key...')
        old_private_pem = input(f'Paste old private key PEM or press Enter to skip: ').strip()
        
        if old_private_pem:
            try:
                old_private_pem_bytes = old_private_pem.encode('utf-8')
                UserKeyManager.load_private_key(old_private_pem_bytes, old_password)
                self.stdout.write('✓ Old key verified')
            except Exception as e:
                raise CommandError(f'Failed to verify old key: {e}')
        else:
            self.stdout.write('⚠️  Skipped old key verification')
        
        # Generate new key
        self.stdout.write(f'\n🔄 Generating new RSA-{key_size} key pair...')
        self.stdout.write('   This may take a few seconds...\n')
        
        try:
            key_data = UserKeyManager.create_user_keypair(
                user_identifier=username,
                password=new_password,
                key_size=key_size
            )
            
            self.stdout.write(self.style.SUCCESS('✓ New key pair generated'))
            self.stdout.write(f'  Key Size: {key_data["key_size"]} bits')
            self.stdout.write(f'  Fingerprint: {key_data["fingerprint"]}')
            
            # Update user record
            old_public_key = user.public_key_pem
            
            with transaction.atomic():
                user.public_key_pem = key_data['public_key_pem'].decode('utf-8')
                user.key_last_rotated = timezone.now()
                user.save(update_fields=['public_key_pem', 'key_last_rotated'])
                
                # Log rotation
                EncryptionAuditLog.log_key_rotation(
                    user=user,
                    details={
                        'username': username,
                        'key_size': key_data['key_size'],
                        'fingerprint': key_data['fingerprint'],
                        'rotated_at': timezone.now().isoformat()
                    }
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ New public key saved to user record'
                ))
            
            # Display new private key
            self.stdout.write(self.style.WARNING(
                '\n' + '=' * 60 + '\n'
                '⚠️  NEW PRIVATE KEY (ENCRYPTED)\n'
                '=' * 60
            ))
            self.stdout.write(key_data['private_key_pem'].decode('utf-8'))
            self.stdout.write(self.style.WARNING('=' * 60))
            
            # Instructions
            self.stdout.write(self.style.WARNING(
                f'\n📝 POST-ROTATION STEPS:\n'
                f'  1. Save NEW private key above to secure location\n'
                f'  2. Store NEW password securely\n'
                f'  3. Update user\'s key file if using file-based storage\n'
                f'  4. New backups will be signed with new key\n'
                f'  5. Keep OLD key if you need to verify old backups\n'
            ))
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ KEY ROTATION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            logger.error(f'User key rotation failed: {e}', exc_info=True)
            raise CommandError(str(e))
