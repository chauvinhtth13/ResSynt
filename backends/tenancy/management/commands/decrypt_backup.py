"""
Decrypt encrypted backup file
"""
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from backends.tenancy.utils.backup_encryption import BackupEncryption
from backends.tenancy.utils.backup_manager import get_backup_manager


class Command(BaseCommand):
    help = 'Decrypt an encrypted backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            'encrypted_file',
            type=str,
            help='Encrypted backup file (absolute path or filename in backups folder)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output path for decrypted file (default: removes .encrypted extension)',
        )
        
        parser.add_argument(
            '--password',
            type=str,
            help='Decryption password (default: use BACKUP_ENCRYPTION_PASSWORD from settings)',
        )

    def handle(self, *args, **options):
        encrypted_file = options['encrypted_file']
        output_path = options.get('output')
        password = options.get('password')
        
        # Find encrypted file
        encrypted_path = Path(encrypted_file)
        
        # If not absolute, try backups folder
        if not encrypted_path.is_absolute():
            backup_manager = get_backup_manager()
            encrypted_path = backup_manager.backup_dir / encrypted_file
        
        # Check if file exists
        if not encrypted_path.exists():
            raise CommandError(f"Encrypted file not found: {encrypted_path}")
        
        # Check if file is encrypted
        if not BackupEncryption.is_encrypted(str(encrypted_path)):
            raise CommandError(
                f"File is not encrypted with our format: {encrypted_path.name}\n"
                f"Expected magic header: PGBACKUP_AES256_V1"
            )
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("DECRYPT BACKUP FILE"))
        self.stdout.write("="*70 + "\n")
        
        # File info
        self.stdout.write("📁 Encrypted File Information")
        self.stdout.write("-"*70)
        self.stdout.write(f"Path: {encrypted_path}")
        self.stdout.write(f"Size: {self._format_size(encrypted_path.stat().st_size)}")
        self.stdout.write()
        
        # Get password
        if password is None:
            # Try to get from settings
            password = getattr(settings, 'BACKUP_ENCRYPTION_PASSWORD', None)
            
        if password is None:
            # Prompt user
            import getpass
            self.stdout.write("🔐 Encrypted backup detected")
            password = getpass.getpass("Enter decryption password: ")
        
        # Decrypt
        self.stdout.write("🔓 Decrypting backup...")
        self.stdout.write()
        
        try:
            result = BackupEncryption.decrypt_file(
                input_path=str(encrypted_path),
                output_path=output_path,
                password=password
            )
            
            if result['status'] != 'success':
                self.stdout.write(self.style.ERROR(
                    f"❌ Decryption failed: {result.get('error', 'Unknown error')}"
                ))
                return
            
            decrypted_path = Path(result['decrypted_path'])
            
            self.stdout.write(self.style.SUCCESS("✓ Decryption successful!"))
            self.stdout.write()
            self.stdout.write("📄 Decrypted File")
            self.stdout.write("-"*70)
            self.stdout.write(f"Path:     {decrypted_path}")
            self.stdout.write(f"Size:     {self._format_size(result['size'])}")
            self.stdout.write(f"Original: {self._format_size(encrypted_path.stat().st_size)}")
            self.stdout.write()
            
            # Show next steps
            self.stdout.write("📋 Next Steps:")
            self.stdout.write("-"*70)
            self.stdout.write("1. Verify backup content:")
            self.stdout.write(f"   python manage.py verify_backup {decrypted_path.name}")
            self.stdout.write()
            self.stdout.write("2. Restore to database:")
            self.stdout.write(f"   python manage.py restore_backup {decrypted_path.name} --database <db_name>")
            self.stdout.write()
            self.stdout.write("3. Or use pg_restore manually:")
            self.stdout.write(f"   pg_restore -h localhost -U user -d dbname {decrypted_path}")
            self.stdout.write()
            
            self.stdout.write(self.style.WARNING(
                "⚠️  Security Notice: Delete decrypted file after use!"
            ))
            self.stdout.write(f"   rm {decrypted_path}")
            self.stdout.write()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            raise
        
        self.stdout.write("="*70)
        self.stdout.write(self.style.SUCCESS("DECRYPTION COMPLETED"))
        self.stdout.write("="*70)
        self.stdout.write()
    
    def _format_size(self, size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
