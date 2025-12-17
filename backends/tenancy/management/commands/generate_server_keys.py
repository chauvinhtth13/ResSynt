"""
Generate Server RSA Keys

Creates RSA-4096 key pair for server and stores in database
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
import getpass
import logging

from backends.tenancy.models import ServerKey
from backends.tenancy.utils.key_manager import ServerKeyManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate RSA-4096 key pair for server'
    
    def add_arguments(self, parser):
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
            '--rotate',
            action='store_true',
            help='Rotate existing key (deactivate old, create new)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if active key exists'
        )
    
    def handle(self, *args, **options):
        key_size = options['key_size']
        rotate = options['rotate']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('SERVER RSA KEY GENERATION'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Check if active key exists
        existing_key = ServerKey.get_active_key()
        if existing_key and not rotate and not force:
            self.stdout.write(self.style.ERROR(
                f'\n✗ Active server key already exists:\n'
                f'  Fingerprint: {existing_key.fingerprint}\n'
                f'  Created: {existing_key.created_at}\n'
                f'  Key Size: {existing_key.key_size} bits\n\n'
                f'Use --rotate to rotate key or --force to replace'
            ))
            return
        
        # Get password
        password = options.get('password')
        if not password:
            self.stdout.write('\nEnter password to encrypt server private key:')
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
        
        self.stdout.write(f'\n📊 Generating RSA-{key_size} key pair...')
        self.stdout.write('   This may take a few seconds...\n')
        
        try:
            # Generate keys
            private_key, public_key = ServerKeyManager.generate_key_pair(key_size)
            
            # Export to PEM
            private_pem = ServerKeyManager.export_private_key(private_key, password)
            public_pem = ServerKeyManager.export_public_key(public_key)
            
            # Get key info
            key_info = ServerKeyManager.get_key_info(public_key)
            
            self.stdout.write(self.style.SUCCESS('✓ Key pair generated'))
            self.stdout.write(f'  Key Size: {key_info["key_size"]} bits')
            self.stdout.write(f'  Fingerprint: {key_info["fingerprint"]}')
            
            # Save to database
            with transaction.atomic():
                # Deactivate existing keys if rotating
                if rotate and existing_key:
                    ServerKey.deactivate_all()
                    self.stdout.write(f'\n✓ Deactivated old key: {existing_key.fingerprint[:16]}...')
                
                # Create new key record
                new_key = ServerKey.objects.create(
                    private_key_pem=private_pem.decode('utf-8'),
                    public_key_pem=public_pem.decode('utf-8'),
                    key_size=key_info['key_size'],
                    fingerprint=key_info['fingerprint'],
                    is_active=True,
                    rotated_from=existing_key if rotate else None,
                    notes=f'Generated via management command (RSA-{key_size})'
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Server key saved to database\n'
                    f'  ID: {new_key.id}\n'
                    f'  Status: ACTIVE'
                ))
            
            # Security reminder
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  SECURITY REMINDER:\n'
                f'  1. Store password in .env: SERVER_KEY_PASSWORD="{password}"\n'
                f'  2. Never commit this password to version control\n'
                f'  3. Backup the password securely\n'
                f'  4. Private key is encrypted in database\n'
            ))
            
            # Validation test
            self.stdout.write('\n🔍 Validating key pair...')
            is_valid = ServerKeyManager.validate_key_pair(private_key, public_key)
            
            if is_valid:
                self.stdout.write(self.style.SUCCESS('✓ Key pair validation: PASSED'))
            else:
                self.stdout.write(self.style.ERROR('✗ Key pair validation: FAILED'))
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ SERVER KEY GENERATION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            logger.error(f'Server key generation failed: {e}', exc_info=True)
