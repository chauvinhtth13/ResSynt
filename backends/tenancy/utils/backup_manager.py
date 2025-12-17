"""
Secure Database Backup Manager
Features:
- PostgreSQL custom format (compressed)
- SHA-256 checksum
- Automatic cleanup
- Support multiple databases
- ✅ CROSS-PLATFORM: Windows + Linux support
- ✅ AES-256-GCM encryption (no GPG needed)
"""
import os
import sys
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manage database backups with compression
    
    ✅ NEW: Auto-detect PostgreSQL on Windows/Linux
    """
    
    def __init__(self):
        """Initialize backup manager"""
        # Backup directory
        self.backup_dir = Path(settings.BASE_DIR) / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Retention policy
        self.retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 90)
        
        # ✅ NEW: Find PostgreSQL binaries
        self.pg_dump_path = self._find_pg_dump()
        
        logger.info(f"BackupManager initialized: {self.backup_dir}")
        logger.info(f"pg_dump path: {self.pg_dump_path}")
    
    def _find_pg_dump(self) -> str:
        """
        ✅ NEW: Auto-detect pg_dump location
        
        Returns:
            Full path to pg_dump executable
        """
        # Check settings first
        custom_path = getattr(settings, 'POSTGRESQL_BIN_PATH', None)
        if custom_path:
            pg_dump = Path(custom_path) / ('pg_dump.exe' if sys.platform == 'win32' else 'pg_dump')
            if pg_dump.exists():
                logger.info(f"Using pg_dump from settings: {pg_dump}")
                return str(pg_dump)
        
        # Try to find in PATH
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['where', 'pg_dump'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ['which', 'pg_dump'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                logger.info(f"Found pg_dump in PATH: {path}")
                return path
                
        except Exception as e:
            logger.debug(f"Could not find pg_dump in PATH: {e}")
        
        # Windows: Search common PostgreSQL installation directories
        if sys.platform == 'win32':
            possible_paths = self._get_windows_postgres_paths()
            
            for path in possible_paths:
                pg_dump = Path(path) / 'pg_dump.exe'
                if pg_dump.exists():
                    logger.info(f"Found pg_dump at: {pg_dump}")
                    return str(pg_dump)
        
        # Linux: Try common paths
        else:
            possible_paths = [
                '/usr/bin/pg_dump',
                '/usr/local/bin/pg_dump',
                '/opt/postgresql/bin/pg_dump',
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    logger.info(f"Found pg_dump at: {path}")
                    return path
        
        # Not found - return default and let it fail with helpful error
        logger.error("Could not find pg_dump. Please set POSTGRESQL_BIN_PATH in settings.")
        return 'pg_dump'
    
    def _get_windows_postgres_paths(self) -> List[str]:
        """
        ✅ NEW: Get possible PostgreSQL paths on Windows
        
        Returns:
            List of possible bin directories
        """
        paths = []
        
        # Common installation directories
        base_paths = [
            r'C:\Program Files\PostgreSQL',
            r'C:\PostgreSQL',
            r'C:\Program Files (x86)\PostgreSQL',
        ]
        
        for base_path in base_paths:
            base = Path(base_path)
            if base.exists():
                # Find all version directories (16, 15, 14, etc.)
                for version_dir in base.iterdir():
                    if version_dir.is_dir():
                        bin_dir = version_dir / 'bin'
                        if bin_dir.exists():
                            paths.append(str(bin_dir))
        
        # Sort by version (newest first)
        paths.sort(reverse=True)
        
        return paths
    
    def create_backup(
        self, 
        database: str = 'default',
        compress: bool = True,
        schemas: list = None
    ) -> Dict[str, any]:
        """
        Create database backup
        
        Args:
            database: Database alias from settings.DATABASES OR database name on PostgreSQL server
            compress: Use compression (recommended)
            schemas: List of schema names to backup (default: all schemas)
                     Example: ['data', 'log'] or ['public', 'data', 'log']
            
        Returns:
            {
                'status': 'success' | 'failed',
                'path': '/path/to/backup.sql.gz',
                'size': 12345678,
                'checksum': 'abc123...',
                'database': 'db_study_43en',
                'timestamp': '20250105_143022',
                'schemas': ['data', 'log']
            }
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get database config
        if database in settings.DATABASES:
            # Use config from settings
            db_config = settings.DATABASES[database]
        else:
            # Database not in settings - use default connection with different dbname
            logger.info(f"Database '{database}' not in settings, using default connection")
            default_config = settings.DATABASES.get('default', {})
            db_config = default_config.copy()
            db_config['NAME'] = database  # Override database name
        
        # Backup filename
        if compress:
            backup_file = f"{database}_{timestamp}.backup"
        else:
            backup_file = f"{database}_{timestamp}.sql"
        
        backup_path = self.backup_dir / backup_file
        
        try:
            logger.info(f"Creating backup: {database}")
            
            # Build pg_dump command
            cmd = self._build_dump_command(
                db_config=db_config,
                output_file=str(backup_path),
                compress=compress,
                schemas=schemas
            )
            
            # Set password via environment
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            # Execute pg_dump
            logger.debug(f"Running: {cmd[0]} ... (password hidden)")
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes max
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Verify file created
            if not backup_path.exists():
                raise Exception("Backup file not created")
            
            # Get file size
            file_size = backup_path.stat().st_size
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            
            logger.info(
                f"✓ Backup created: {backup_file}\n"
                f"  Size: {self._format_size(file_size)}\n"
                f"  Checksum: {checksum[:16]}..."
            )
            
            # Cleanup old backups
            self._cleanup_old_backups(database)
            
            return {
                'status': 'success',
                'path': str(backup_path),
                'size': file_size,
                'checksum': checksum,
                'database': database,
                'timestamp': timestamp,
                'compressed': compress,
                'schemas': schemas if schemas else 'all'
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Backup timeout for {database}")
            return {
                'status': 'failed',
                'error': 'Backup timeout (>30 minutes)'
            }
            
        except Exception as e:
            logger.error(f"Backup failed for {database}: {e}", exc_info=True)
            
            # Cleanup partial file
            if backup_path.exists():
                backup_path.unlink()
            
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _build_dump_command(
        self,
        db_config: Dict,
        output_file: str,
        compress: bool,
        schemas: list = None
    ) -> list:
        """
        Build pg_dump command
        
        ✅ UPDATED: Use full path to pg_dump + support schema filtering
        
        Args:
            schemas: List of schema names to backup (default: all schemas)
        
        Returns:
            ['C:/Program Files/PostgreSQL/16/bin/pg_dump.exe', '-h', 'localhost', ...]
        """
        cmd = [
            self.pg_dump_path,  # ✅ Use detected path
            '-h', db_config['HOST'],
            '-p', str(db_config['PORT']),
            '-U', db_config['USER'],
            '-d', db_config['NAME'],
        ]
        
        # Add schema filters if specified
        if schemas:
            for schema in schemas:
                cmd.extend(['-n', schema])
            logger.info(f"Backing up schemas: {', '.join(schemas)}")
        else:
            # Backup ALL schemas (pg_dump default behavior)
            logger.info("Backing up all schemas")
        
        if compress:
            # Custom format (compressed, portable)
            cmd.extend([
                '-F', 'c',  # Format: custom
                '-Z', '9',  # Compression level: 9 (max)
            ])
        else:
            # Plain SQL format
            cmd.extend([
                '-F', 'p',  # Format: plain
            ])
        
        # Output file
        cmd.extend(['-f', output_file])
        
        return cmd
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA-256 checksum
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex string (64 characters)
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _cleanup_old_backups(self, database: str) -> int:
        """
        Remove backups older than retention period
        
        Args:
            database: Database name
            
        Returns:
            Number of files removed
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        # Pattern: database_YYYYMMDD_HHMMSS.*
        pattern = f"{database}_*.backup"
        removed = 0
        
        for backup_file in self.backup_dir.glob(pattern):
            try:
                # Parse timestamp from filename
                # Format: db_study_43en_20250105_143022.backup
                parts = backup_file.stem.split('_')
                
                # Find date and time parts
                date_str = None
                time_str = None
                
                for i, part in enumerate(parts):
                    if len(part) == 8 and part.isdigit():
                        date_str = part
                        if i + 1 < len(parts):
                            time_str = parts[i + 1]
                        break
                
                if not date_str or not time_str:
                    continue
                
                # Parse datetime
                backup_datetime = datetime.strptime(
                    f"{date_str}_{time_str}",
                    '%Y%m%d_%H%M%S'
                )
                
                # Check if old
                if backup_datetime < cutoff_date:
                    backup_file.unlink()
                    removed += 1
                    logger.debug(f"Removed old backup: {backup_file.name}")
                    
            except Exception as e:
                logger.warning(f"Error processing {backup_file}: {e}")
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} old backup(s)")
        
        return removed
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Format size in human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted string (e.g., "2.3 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def list_backups(self, database: Optional[str] = None) -> list:
        """
        List all backups
        
        Args:
            database: Filter by database (optional)
            
        Returns:
            List of backup info dictionaries
        """
        backups = []
        
        pattern = f"{database}_*.backup" if database else "*.backup"
        
        for backup_file in sorted(self.backup_dir.glob(pattern)):
            try:
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size': backup_file.stat().st_size,
                    'size_human': self._format_size(backup_file.stat().st_size),
                    'modified': datetime.fromtimestamp(backup_file.stat().st_mtime),
                })
            except Exception as e:
                logger.warning(f"Error reading {backup_file}: {e}")
        
        return backups
    
    def verify_backup(self, backup_path: str) -> Dict[str, any]:
        """
        Verify backup integrity
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            {
                'valid': True/False,
                'checksum': 'abc123...',
                'size': 12345678
            }
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {
                'valid': False,
                'error': 'File not found'
            }
        
        try:
            checksum = self._calculate_checksum(backup_file)
            size = backup_file.stat().st_size
            
            # Basic validation: check if it's a PostgreSQL backup
            with open(backup_file, 'rb') as f:
                header = f.read(5)
                is_pg_backup = header == b'PGDMP'  # PostgreSQL custom format magic bytes
            
            return {
                'valid': is_pg_backup,
                'checksum': checksum,
                'size': size,
                'is_postgresql_backup': is_pg_backup
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }



    def encrypt_backup(
            self, 
            backup_path: str, 
            password: str = None,
            remove_original: bool = False
        ) -> Dict[str, any]:
            """
            Encrypt backup with AES-256-GCM (Python native - no GPG needed)
            
            Args:
                backup_path: Path to backup file
                password: Encryption password (or use BACKUP_ENCRYPTION_PASSWORD from settings)
                remove_original: Delete original file after encryption
                
            Returns:
                {
                    'status': 'success' | 'failed',
                    'encrypted_path': '/path/to/backup.backup.encrypted',
                    'size': 12345678
                }
            """
            from backends.tenancy.utils.backup_encryption import BackupEncryption
            
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return {
                    'status': 'failed',
                    'error': 'Backup file not found'
                }
            
            # Get password
            if password is None:
                password = getattr(settings, 'BACKUP_ENCRYPTION_PASSWORD', None)
                if not password:
                    return {
                        'status': 'failed',
                        'error': 'No encryption password. Set BACKUP_ENCRYPTION_PASSWORD in settings or use --password'
                    }
            
            encrypted_path = f"{backup_path}.encrypted"
            
            try:
                logger.info(f"Encrypting: {backup_file.name}")
                
                # Use Python cryptography library
                result = BackupEncryption.encrypt_file(
                    input_path=str(backup_path),
                    output_path=encrypted_path,
                    password=password
                )
                
                if result['status'] != 'success':
                    raise Exception(result.get('error', 'Unknown encryption error'))
                
                logger.info(f"✓ Encrypted: {Path(encrypted_path).name} ({self._format_size(result['size'])})")
                
                # Remove original if requested
                if remove_original:
                    backup_file.unlink()
                    logger.info(f"✓ Removed original: {backup_file.name}")
                
                return {
                    'status': 'success',
                    'encrypted_path': encrypted_path,
                    'size': result['size'],
                    'removed_original': remove_original,
                    'algorithm': 'AES-256-GCM'
                }
                
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                encrypted_file = Path(encrypted_path)
                if encrypted_file.exists():
                    encrypted_file.unlink()
                return {
                    'status': 'failed',
                    'error': str(e)
                }
        
    def decrypt_backup(
            self, 
            encrypted_path: str, 
            password: str,
            output_path: str = None
        ) -> Dict[str, any]:
            """
            Decrypt GPG-encrypted backup
            
            Args:
                encrypted_path: Path to .gpg file
                password: Decryption password
                output_path: Output path (optional)
                
            Returns:
                {
                    'status': 'success' | 'failed',
                    'decrypted_path': '/path/to/backup.backup',
                    'size': 12345678
                }
            """
            encrypted_file = Path(encrypted_path)
            
            if not encrypted_file.exists():
                return {
                    'status': 'failed',
                    'error': 'Encrypted file not found'
                }
            
            if output_path is None:
                output_path = str(encrypted_file).replace('.gpg', '')
            
            output_file = Path(output_path)
            
            try:
                logger.info(f"Decrypting: {encrypted_file.name}")
                
                cmd = [
                    'gpg',
                    '--batch',
                    '--yes',
                    '--passphrase', password,
                    '--decrypt',
                    '-o', str(output_file),
                    str(encrypted_file)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    raise Exception(f"GPG decrypt failed: {result.stderr}")
                
                if not output_file.exists():
                    raise Exception("Decrypted file not created")
                
                file_size = output_file.stat().st_size
                
                logger.info(f"✓ Decrypted: {output_file.name} ({self._format_size(file_size)})")
                
                return {
                    'status': 'success',
                    'decrypted_path': str(output_file),
                    'size': file_size
                }
                
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                if output_file.exists():
                    output_file.unlink()
                return {
                    'status': 'failed',
                    'error': str(e)
                }

# ==========================================
# GLOBAL INSTANCE
# ==========================================

_backup_manager = None

def get_backup_manager() -> BackupManager:
    """
    Get global backup manager instance
    
    Returns:
        BackupManager instance
    """
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager