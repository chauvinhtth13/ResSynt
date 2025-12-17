"""
Secure Database Backup Manager.

Features:
- PostgreSQL custom format (compressed)
- SHA-256 checksum verification
- Automatic cleanup with retention policy
- Cross-platform support (Windows/Linux)
- Secure encryption via GPG
"""
import hashlib
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from django.conf import settings

logger = logging.getLogger(__name__)


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


class BackupManager:
    """
    Database backup manager with compression and encryption.
    
    Security notes:
    - Passwords passed via environment variables (not command line)
    - GPG encryption uses stdin for passphrase
    - Backup files have restricted permissions
    """
    
    def __init__(self):
        self.backup_dir = Path(settings.BASE_DIR) / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on backup directory
        if sys.platform != 'win32':
            os.chmod(self.backup_dir, 0o700)
        
        self.retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 90)
        self.pg_dump_path = self._find_pg_dump()
    
    def _find_pg_dump(self) -> str:
        """Find pg_dump executable."""
        # Check settings first
        custom_path = getattr(settings, 'POSTGRESQL_BIN_PATH', None)
        if custom_path:
            exe = 'pg_dump.exe' if sys.platform == 'win32' else 'pg_dump'
            pg_dump = Path(custom_path) / exe
            if pg_dump.exists():
                return str(pg_dump)
        
        # Try PATH
        try:
            cmd = ['where', 'pg_dump'] if sys.platform == 'win32' else ['which', 'pg_dump']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        
        # Platform-specific search
        if sys.platform == 'win32':
            for base in [r'C:\Program Files\PostgreSQL', r'C:\PostgreSQL']:
                base_path = Path(base)
                if base_path.exists():
                    for ver_dir in sorted(base_path.iterdir(), reverse=True):
                        pg_dump = ver_dir / 'bin' / 'pg_dump.exe'
                        if pg_dump.exists():
                            return str(pg_dump)
        else:
            for path in ['/usr/bin/pg_dump', '/usr/local/bin/pg_dump']:
                if Path(path).exists():
                    return path
        
        logger.warning("pg_dump not found. Set POSTGRESQL_BIN_PATH in settings.")
        return 'pg_dump'
    
    def create_backup(self, database: str = 'default', compress: bool = True) -> Dict[str, Any]:
        """
        Create database backup.
        
        Args:
            database: Database alias from settings.DATABASES
            compress: Use compression (recommended)
            
        Returns:
            Result dictionary with status, path, size, checksum
        """
        if database not in settings.DATABASES:
            return {'status': 'failed', 'error': f"Database '{database}' not found"}
        
        db_config = settings.DATABASES[database]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = '.backup' if compress else '.sql'
        backup_path = self.backup_dir / f"{database}_{timestamp}{ext}"
        
        try:
            cmd = self._build_dump_command(db_config, str(backup_path), compress)
            
            # Pass password via environment (secure)
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=1800
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr[:200]}")
            
            if not backup_path.exists():
                raise Exception("Backup file not created")
            
            # Set restrictive permissions
            if sys.platform != 'win32':
                os.chmod(backup_path, 0o600)
            
            file_size = backup_path.stat().st_size
            checksum = self._calculate_checksum(backup_path)
            
            logger.info(f"Backup created: {backup_path.name} ({format_size(file_size)})")
            
            # Cleanup old backups
            self._cleanup_old_backups(database)
            
            return {
                'status': 'success',
                'path': str(backup_path),
                'size': file_size,
                'checksum': checksum,
                'database': database,
                'timestamp': timestamp,
            }
            
        except subprocess.TimeoutExpired:
            return {'status': 'failed', 'error': 'Backup timeout (>30 minutes)'}
        except Exception as e:
            if backup_path.exists():
                backup_path.unlink()
            logger.error(f"Backup failed: {type(e).__name__}")
            return {'status': 'failed', 'error': str(e)}
    
    def _build_dump_command(self, db_config: Dict, output_file: str, compress: bool) -> List[str]:
        """Build pg_dump command."""
        cmd = [
            self.pg_dump_path,
            '-h', db_config['HOST'],
            '-p', str(db_config['PORT']),
            '-U', db_config['USER'],
            '-d', db_config['NAME'],
        ]
        
        if compress:
            cmd.extend(['-F', 'c', '-Z', '9'])
        else:
            cmd.extend(['-F', 'p'])
        
        cmd.extend(['-f', output_file])
        return cmd
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _cleanup_old_backups(self, database: str) -> None:
        """Remove backups older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0
        
        for backup_file in self.backup_dir.glob(f"{database}_*.backup"):
            try:
                # Parse timestamp from filename
                parts = backup_file.stem.split('_')
                for i, part in enumerate(parts):
                    if len(part) == 8 and part.isdigit() and i + 1 < len(parts):
                        backup_dt = datetime.strptime(f"{part}_{parts[i+1]}", '%Y%m%d_%H%M%S')
                        if backup_dt < cutoff:
                            backup_file.unlink()
                            removed += 1
                        break
            except Exception:
                pass
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} old backup(s)")
    
    def list_backups(self, database: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all backups."""
        pattern = f"{database}_*.backup" if database else "*.backup"
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob(pattern)):
            try:
                stat = backup_file.stat()
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'size_human': format_size(stat.st_size),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                })
            except Exception:
                pass
        
        return backups
    
    def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """Verify backup integrity."""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {'valid': False, 'error': 'File not found'}
        
        try:
            with open(backup_file, 'rb') as f:
                header = f.read(5)
                is_pg_backup = header == b'PGDMP'
            
            return {
                'valid': is_pg_backup,
                'checksum': self._calculate_checksum(backup_file),
                'size': backup_file.stat().st_size,
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def encrypt_backup(
        self, 
        backup_path: str, 
        password: Optional[str] = None,
        remove_original: bool = False
    ) -> Dict[str, Any]:
        """
        Encrypt backup with GPG (AES-256).
        
        Security: Password passed via stdin, not command line.
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            return {'status': 'failed', 'error': 'Backup file not found'}
        
        password = password or getattr(settings, 'BACKUP_ENCRYPTION_PASSWORD', None)
        if not password:
            return {'status': 'failed', 'error': 'No encryption password provided'}
        
        encrypted_path = Path(f"{backup_path}.gpg")
        
        try:
            # Use --passphrase-fd 0 to read password from stdin (more secure)
            cmd = [
                'gpg', '--batch', '--yes',
                '--passphrase-fd', '0',
                '--symmetric', '--cipher-algo', 'AES256',
                '-o', str(encrypted_path),
                str(backup_path)
            ]
            
            result = subprocess.run(
                cmd,
                input=password,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise Exception(f"GPG failed: {result.stderr[:100]}")
            
            if not encrypted_path.exists():
                raise Exception("Encrypted file not created")
            
            # Set restrictive permissions
            if sys.platform != 'win32':
                os.chmod(encrypted_path, 0o600)
            
            file_size = encrypted_path.stat().st_size
            
            if remove_original:
                backup_file.unlink()
            
            return {
                'status': 'success',
                'encrypted_path': str(encrypted_path),
                'size': file_size,
            }
            
        except Exception as e:
            if encrypted_path.exists():
                encrypted_path.unlink()
            return {'status': 'failed', 'error': str(e)}
    
    def decrypt_backup(
        self,
        encrypted_path: str,
        password: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Decrypt GPG-encrypted backup."""
        encrypted_file = Path(encrypted_path)
        if not encrypted_file.exists():
            return {'status': 'failed', 'error': 'Encrypted file not found'}
        
        output_file = Path(output_path or str(encrypted_file).replace('.gpg', ''))
        
        try:
            cmd = [
                'gpg', '--batch', '--yes',
                '--passphrase-fd', '0',
                '--decrypt',
                '-o', str(output_file),
                str(encrypted_file)
            ]
            
            result = subprocess.run(
                cmd,
                input=password,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise Exception(f"GPG decrypt failed: {result.stderr[:100]}")
            
            return {
                'status': 'success',
                'decrypted_path': str(output_file),
                'size': output_file.stat().st_size,
            }
            
        except Exception as e:
            if output_file.exists():
                output_file.unlink()
            return {'status': 'failed', 'error': str(e)}


# Global instance
_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Get global backup manager instance."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager