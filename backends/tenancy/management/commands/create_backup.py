"""
Management command to create database backups
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from backends.tenancy.utils.backup_manager import get_backup_manager


class Command(BaseCommand):
    help = 'Create encrypted database backup'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            default='default',
            help='Database to backup (default: default)'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Backup all databases'
        )
        
        parser.add_argument(
            '--list',
            action='store_true',
            help='List existing backups'
        )
        
        parser.add_argument(
            '--verify',
            type=str,
            help='Verify backup file'
        )
        parser.add_argument(
            '--encrypt',
            action='store_true',
            help='Encrypt backup with GPG AES-256'
        )
        
        parser.add_argument(
            '--password',
            type=str,
            help='Encryption/decryption password'
        )
        
        parser.add_argument(
            '--decrypt',
            type=str,
            help='Decrypt backup file'
        )
        
        parser.add_argument(
            '--remove-original',
            action='store_true',
            help='Remove original backup after encryption'
        )
    
    def handle(self, *args, **options):
        backup_manager = get_backup_manager()

        # Decrypt backup
        if options.get('decrypt'):
            self.decrypt_backup(backup_manager, options['decrypt'], options.get('password'))
            return
        
        # List backups
        if options['list']:
            self.list_backups(backup_manager, options.get('database'))
            return
        
        # Verify backup
        if options['verify']:
            self.verify_backup(backup_manager, options['verify'])
            return
        
        # Create backups
        if options['all']:
            self.backup_all_databases(backup_manager)
        else:
            self.backup_single_database(backup_manager, options['database'])
    
    def backup_single_database(self, backup_manager, database, options=None):
            """Backup single database"""
            if options is None:
                options = {}
                
            self.stdout.write(f"\n📦 Creating backup for: {database}")
            self.stdout.write("─" * 60)
            
            result = backup_manager.create_backup(database)
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS("\n✓ Backup created successfully!"))
                self.stdout.write(f"  Database:  {result['database']}")
                self.stdout.write(f"  Path:      {result['path']}")
                self.stdout.write(f"  Size:      {backup_manager._format_size(result['size'])}")
                self.stdout.write(f"  Checksum:  {result['checksum'][:32]}...")
                self.stdout.write(f"  Timestamp: {result['timestamp']}")
                
                # ✅ NEW: Encrypt if requested
                if options.get('encrypt'):
                    self.encrypt_backup(
                        backup_manager,
                        result['path'],
                        options.get('password'),
                        options.get('remove_original', False)
                    )
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ Backup failed: {result.get('error')}"))
    
    def backup_all_databases(self, backup_manager, options=None):
            """Backup all databases"""
            if options is None:
                options = {}
                
            databases = list(settings.DATABASES.keys())
            
            self.stdout.write(f"\n📦 Backing up {len(databases)} database(s)...")
            self.stdout.write("═" * 60)
            
            results = []
            
            for database in databases:
                self.stdout.write(f"\n{database}:")
                self.stdout.write("─" * 60)
                
                result = backup_manager.create_backup(database)
                results.append(result)
                
                if result['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ {result['path']}\n"
                        f"  Size: {backup_manager._format_size(result['size'])}"
                    ))
                    
                    # ✅ NEW: Encrypt if requested
                    if options.get('encrypt'):
                        self.encrypt_backup(
                            backup_manager,
                            result['path'],
                            options.get('password'),
                            options.get('remove_original', False)
                        )
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  ✗ {result.get('error', 'Unknown error')}"
                    ))
            
            # Summary
            success_count = sum(1 for r in results if r['status'] == 'success')
            self.stdout.write("\n" + "═" * 60)
            self.stdout.write(f"Summary: {success_count}/{len(databases)} successful")
            self.stdout.write("═" * 60 + "\n")
    
    def list_backups(self, backup_manager, database=None):
        """List existing backups"""
        backups = backup_manager.list_backups(database)
        
        if not backups:
            self.stdout.write("No backups found.")
            return
        
        self.stdout.write(f"\n📋 Found {len(backups)} backup(s):")
        self.stdout.write("═" * 80)
        
        for backup in backups:
            self.stdout.write(
                f"  {backup['filename']}\n"
                f"    Size:     {backup['size_human']}\n"
                f"    Modified: {backup['modified']}\n"
            )
        
        self.stdout.write("═" * 80 + "\n")
    
    def verify_backup(self, backup_manager, backup_path):
        """Verify backup integrity"""
        self.stdout.write(f"\n🔍 Verifying backup: {backup_path}")
        self.stdout.write("─" * 60)
        
        result = backup_manager.verify_backup(backup_path)
        
        if result.get('valid'):
            self.stdout.write(self.style.SUCCESS("\n✓ Backup is valid!"))
            self.stdout.write(f"  Checksum: {result['checksum'][:32]}...")
            self.stdout.write(f"  Size:     {backup_manager._format_size(result['size'])}")
        else:
            self.stdout.write(self.style.ERROR(
                f"\n✗ Backup is invalid: {result.get('error', 'Unknown error')}"
            ))

    def encrypt_backup(self, backup_manager, backup_path, password, remove_original):
            """Encrypt backup with GPG"""
            self.stdout.write(f"\n🔒 Encrypting backup...")
            self.stdout.write("─" * 60)
            
            result = backup_manager.encrypt_backup(backup_path, password, remove_original)
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS("\n✓ Encrypted successfully!"))
                self.stdout.write(f"  Path: {result['encrypted_path']}")
                self.stdout.write(f"  Size: {backup_manager._format_size(result['size'])}")
                if result['removed_original']:
                    self.stdout.write(f"  Original: Removed ✓")
            else:
                self.stdout.write(self.style.ERROR(
                    f"\n✗ Encryption failed: {result.get('error')}"
                ))
        
    def decrypt_backup(self, backup_manager, encrypted_path, password):
            """Decrypt backup"""
            if not password:
                self.stdout.write(self.style.ERROR(
                    "\n✗ Password required for decryption. Use --password option."
                ))
                return
            
            self.stdout.write(f"\n🔓 Decrypting: {encrypted_path}")
            self.stdout.write("─" * 60)
            
            result = backup_manager.decrypt_backup(encrypted_path, password)
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS("\n✓ Decrypted successfully!"))
                self.stdout.write(f"  Path: {result['decrypted_path']}")
                self.stdout.write(f"  Size: {backup_manager._format_size(result['size'])}")
            else:
                self.stdout.write(self.style.ERROR(
                    f"\n✗ Decryption failed: {result.get('error')}"
                ))