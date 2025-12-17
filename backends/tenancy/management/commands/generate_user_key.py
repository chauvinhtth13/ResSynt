"""
Generate User RSA Key

Creates RSA-4096 key pair for a user and stores public key in database
Private key is returned to admin for secure storage
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
    help = 'Generate RSA key pair for a user'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username to generate key for'
        )
        parser.add_argument(
            '--key-size',
            type=int,
            default=4096,
            help='RSA key size in bits (default: 4096)'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password to encrypt private key (will prompt if not provided)'
        )
        parser.add_argument(
            '--export-private',
            action='store_true',
            help='Export private key to file (WARNING: insecure)'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        key_size = options['key_size']
        export_private = options['export_private']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'USER RSA KEY GENERATION: {username}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        # Check if user already has key
        if user.public_key_pem:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  User already has a key:\n'
                f'  Generated: {user.key_generated_at}\n'
                f'  Last Rotated: {user.key_last_rotated or "Never"}\n'
            ))
            
            confirm = input('\nReplace existing key? This will invalidate old signatures. (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled')
                return
        
        # Get password
        password = options.get('password')
        if not password:
            self.stdout.write('\nEnter password to encrypt user private key:')
            password = getpass.getpass('Password: ')
            password_confirm = getpass.getpass('Confirm password: ')
            
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('✗ Passwords do not match'))
                return
        
        if len(password) < 16:
            self.stdout.write(self.style.ERROR(
                '✗ Password must be at least 16 characters'
            ))
            return
        
        self.stdout.write(f'\n📊 Generating RSA-{key_size} key pair for {username}...')
        self.stdout.write('   This may take a few seconds...\n')
        
        try:
            # Generate key pair
            key_data = UserKeyManager.create_user_keypair(
                user_identifier=username,
                password=password,
                key_size=key_size
            )
            
            self.stdout.write(self.style.SUCCESS('✓ Key pair generated'))
            self.stdout.write(f'  Key Size: {key_data["key_size"]} bits')
            self.stdout.write(f'  Fingerprint: {key_data["fingerprint"]}')
            
            # Update user record
            with transaction.atomic():
                had_key = bool(user.public_key_pem)
                
                user.public_key_pem = key_data['public_key_pem'].decode('utf-8')
                user.key_generated_at = timezone.now()
                
                if had_key:
                    user.key_last_rotated = timezone.now()
                
                user.save(update_fields=[
                    'public_key_pem', 
                    'key_generated_at', 
                    'key_last_rotated'
                ])
                
                # Log to audit
                EncryptionAuditLog.log_key_generation(
                    user=user,
                    details={
                        'key_size': key_data['key_size'],
                        'fingerprint': key_data['fingerprint'],
                        'action': 'rotation' if had_key else 'initial_generation'
                    }
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Public key saved to user record\n'
                    f'  User ID: {user.id}\n'
                    f'  Username: {user.username}'
                ))
            
            # Display private key (for admin to store securely)
            self.stdout.write(self.style.WARNING(
                '\n' + '=' * 60 + '\n'
                '⚠️  PRIVATE KEY (ENCRYPTED)\n'
                '=' * 60
            ))
            self.stdout.write(key_data['private_key_pem'].decode('utf-8'))
            self.stdout.write(self.style.WARNING('=' * 60))
            
            # Security reminder
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  SECURITY INSTRUCTIONS:\n'
                f'  1. Copy the PRIVATE KEY above to a secure location\n'
                f'  2. Store password securely (never in plain text)\n'
                f'  3. User needs private key + password to sign backups\n'
                f'  4. Public key is stored in database for verification\n'
                f'  5. NEVER commit private key to version control\n'
            ))
            
            # Export to file if requested
            if export_private:
                output_file = f'{username}_private_key.pem'
                with open(output_file, 'wb') as f:
                    f.write(key_data['private_key_pem'])
                
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  Private key exported to: {output_file}\n'
                    f'   Secure this file immediately!\n'
                ))
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ USER KEY GENERATION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            logger.error(f'User key generation failed: {e}', exc_info=True)
