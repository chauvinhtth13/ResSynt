"""
Verify backup file integrity and content
"""
import subprocess
import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from backends.tenancy.utils.backup_manager import get_backup_manager


class Command(BaseCommand):
    help = 'Verify backup file integrity and show content summary'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Backup file path (absolute or relative to backups folder)'
        )
        
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed table structure'
        )
        
        parser.add_argument(
            '--list-tables',
            action='store_true',
            help='List all tables in backup'
        )
        
        parser.add_argument(
            '--password',
            type=str,
            help='Decryption password for encrypted backups'
        )
        
        parser.add_argument(
            '--keep-decrypted',
            action='store_true',
            help='Keep decrypted file after verification (default: delete)'
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        detailed = options['detailed']
        list_tables = options['list_tables']
        password = options.get('password')
        keep_decrypted = options.get('keep_decrypted', False)
        
        # Convert to Path
        backup_path = Path(backup_file)
        
        # If not absolute, try backups folder
        if not backup_path.is_absolute():
            backup_manager = get_backup_manager()
            backup_path = backup_manager.backup_dir / backup_file
        
        # Check if file exists
        if not backup_path.exists():
            raise CommandError(f"Backup file not found: {backup_path}")
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("BACKUP VERIFICATION"))
        self.stdout.write("="*70 + "\n")
        
        # File info
        self.stdout.write("📁 File Information")
        self.stdout.write("-"*70)
        self.stdout.write(f"Path: {backup_path}")
        self.stdout.write(f"Size: {self._format_size(backup_path.stat().st_size)}")
        self.stdout.write(f"Created: {backup_path.stat().st_ctime}")
        self.stdout.write()
        
        # Checksum verification
        self.stdout.write("🔐 Checksum Verification")
        self.stdout.write("-"*70)
        
        try:
            checksum = self._calculate_checksum(backup_path)
            self.stdout.write(self.style.SUCCESS(f"✓ SHA-256: {checksum[:64]}"))
            self.stdout.write(f"  Full: {checksum}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to calculate checksum: {e}"))
        
        self.stdout.write()
        
        # Check if encrypted
        self.stdout.write("🔒 Encryption Status")
        self.stdout.write("-"*70)
        
        is_encrypted = self._check_if_encrypted(backup_path)
        actual_backup_path = backup_path
        decrypted_temp_path = None
        
        if is_encrypted:
            self.stdout.write(self.style.WARNING("✓ File is ENCRYPTED (AES-256)"))
            self.stdout.write()
            
            # Decrypt for verification
            if password is None:
                # Try to get from settings
                password = getattr(settings, 'BACKUP_ENCRYPTION_PASSWORD', None)
                
            if password is None:
                # Prompt user
                import getpass
                self.stdout.write("🔐 Encrypted backup detected")
                password = getpass.getpass("Enter decryption password: ")
            
            # Decrypt to temp file
            backup_manager = get_backup_manager()
            
            self.stdout.write("Decrypting backup for verification...")
            decrypt_result = backup_manager.decrypt_backup(
                encrypted_path=str(backup_path),
                password=password,
                output_path=None  # Will create temp file
            )
            
            if decrypt_result['status'] != 'success':
                self.stdout.write(self.style.ERROR(
                    f"❌ Decryption failed: {decrypt_result.get('error', 'Unknown error')}"
                ))
                return
            
            decrypted_temp_path = Path(decrypt_result['decrypted_path'])
            actual_backup_path = decrypted_temp_path
            self.stdout.write(self.style.SUCCESS("✓ Decryption successful"))
            self.stdout.write()
        else:
            self.stdout.write(self.style.SUCCESS("✓ File is NOT encrypted (plain PostgreSQL backup)"))
        
        self.stdout.write()
        
        # Verify backup structure
        self.stdout.write("🗄️  Backup Content Verification")
        self.stdout.write("-"*70)
        
        try:
            # Use pg_restore to list contents
            result = self._run_pg_restore_list(actual_backup_path)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS("✓ Backup file is valid and readable"))
                self.stdout.write()
                
                # Parse and display content
                self._display_backup_content(result['output'], detailed, list_tables)
                
            else:
                self.stdout.write(self.style.ERROR(f"❌ Failed to read backup: {result['error']}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Verification failed: {e}"))
        
        finally:
            # Cleanup decrypted temp file
            if decrypted_temp_path and decrypted_temp_path.exists():
                if not keep_decrypted:
                    decrypted_temp_path.unlink()
                    self.stdout.write(self.style.WARNING("(Decrypted temp file removed for security)"))
                else:
                    self.stdout.write(f"Decrypted file kept at: {decrypted_temp_path}")
        
        self.stdout.write()
        self.stdout.write("="*70)
        self.stdout.write(self.style.SUCCESS("VERIFICATION COMPLETED"))
        self.stdout.write("="*70)
        self.stdout.write()

    def _format_size(self, size_bytes):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def _calculate_checksum(self, file_path):
        """Calculate SHA-256 checksum"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(65536)  # 64KB chunks
                if not data:
                    break
                sha256.update(data)
        
        return sha256.hexdigest()

    def _check_if_encrypted(self, file_path):
        """Check if file is GPG encrypted"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                
            # GPG encrypted files start with specific bytes
            # ASCII armor: -----BEGIN PGP MESSAGE-----
            # Binary: \x85 or \x84 (packet tag)
            if header.startswith(b'-----BEGIN PGP'):
                return True
            if len(header) > 0 and header[0] in (0x85, 0x84, 0x8c):
                return True
                
            return False
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not check encryption: {e}"))
            return False

    def _run_pg_restore_list(self, backup_path):
        """Run pg_restore --list to get backup contents"""
        try:
            # Find pg_restore
            backup_manager = get_backup_manager()
            pg_restore_path = backup_manager.pg_dump_path.replace('pg_dump', 'pg_restore')
            
            # Run pg_restore --list
            cmd = [
                pg_restore_path,
                '--list',
                str(backup_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _display_backup_content(self, output, detailed, list_tables):
        """Parse and display backup content"""
        lines = output.strip().split('\n')
        
        # Parse content
        tables = []
        sequences = []
        indexes = []
        constraints = []
        schemas = []
        
        for line in lines:
            if not line.strip() or line.startswith(';'):
                continue
                
            # Format: "243; 1259 72318 TABLE management account_emailaddress ressync_admin"
            # Split by semicolon first, then by spaces
            parts = line.split()
            if len(parts) < 4:
                continue
            
            # Entry type is at index 3 (after ID; OID TYPE_OID)
            entry_type = parts[3] if len(parts) > 3 else ''
            
            if entry_type == 'SCHEMA':
                schema_name = parts[5] if len(parts) > 5 else 'unknown'
                schemas.append(schema_name)
            elif entry_type == 'TABLE':
                # Format: TABLE schema table_name owner
                schema = parts[4] if len(parts) > 4 else ''
                table_name = parts[5] if len(parts) > 5 else 'unknown'
                full_name = f"{schema}.{table_name}" if schema and schema != '-' else table_name
                tables.append(full_name)
            elif entry_type == 'SEQUENCE':
                schema = parts[4] if len(parts) > 4 else ''
                sequence_name = parts[5] if len(parts) > 5 else 'unknown'
                full_name = f"{schema}.{sequence_name}" if schema and schema != '-' else sequence_name
                sequences.append(full_name)
            elif entry_type == 'INDEX':
                schema = parts[4] if len(parts) > 4 else ''
                index_name = parts[5] if len(parts) > 5 else 'unknown'
                full_name = f"{schema}.{index_name}" if schema and schema != '-' else index_name
                indexes.append(index_name)
            elif 'CONSTRAINT' in entry_type:
                constraint_name = parts[5] if len(parts) > 5 else 'unknown'
                constraints.append(constraint_name)
        
        # Display summary
        self.stdout.write("📊 Content Summary:")
        self.stdout.write(f"  Schemas: {len(schemas)}")
        self.stdout.write(f"  Tables: {len(tables)}")
        self.stdout.write(f"  Sequences: {len(sequences)}")
        self.stdout.write(f"  Indexes: {len(indexes)}")
        self.stdout.write(f"  Constraints: {len(constraints)}")
        
        if schemas:
            self.stdout.write(f"\n📦 Schemas: {', '.join(sorted(set(schemas)))}")
        
        self.stdout.write()
        
        # List tables if requested
        if list_tables and tables:
            self.stdout.write("📋 Tables in backup:")
            self.stdout.write("-"*70)
            
            # Group tables by schema
            schema_tables = {}
            for table in tables:
                if '.' in table:
                    schema, tbl = table.split('.', 1)
                    if schema not in schema_tables:
                        schema_tables[schema] = []
                    schema_tables[schema].append(tbl)
                else:
                    if 'public' not in schema_tables:
                        schema_tables['public'] = []
                    schema_tables['public'].append(table)
            
            # Display by schema
            for schema in sorted(schema_tables.keys()):
                tables_list = sorted(schema_tables[schema])
                self.stdout.write(f"\n🔹 Schema: {schema} ({len(tables_list)} tables)")
                
                # Categorize tables
                django_tables = [t for t in tables_list if any(
                    prefix in t.lower() for prefix in 
                    ['auth_', 'django_', 'axes_', 'account_', 'allauth_']
                )]
                
                app_tables = [t for t in tables_list if t not in django_tables]
                
                if django_tables:
                    self.stdout.write(f"  Django System ({len(django_tables)}):")
                    for table in django_tables[:15]:
                        self.stdout.write(f"    • {table}")
                    if len(django_tables) > 15:
                        self.stdout.write(f"    ... and {len(django_tables) - 15} more")
                
                if app_tables:
                    self.stdout.write(f"  Application Tables ({len(app_tables)}):")
                    for table in app_tables[:15]:
                        self.stdout.write(f"    • {table}")
                    if len(app_tables) > 15:
                        self.stdout.write(f"    ... and {len(app_tables) - 15} more")
            
            self.stdout.write()
        
        # Detailed mode
        if detailed:
            self.stdout.write("📝 Detailed Content (first 50 lines):")
            self.stdout.write("-"*70)
            for i, line in enumerate(lines[:50]):
                if not line.startswith(';'):
                    self.stdout.write(f"  {line}")
            if len(lines) > 50:
                self.stdout.write(f"  ... and {len(lines) - 50} more lines")
            self.stdout.write()
