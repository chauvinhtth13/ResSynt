"""
Cross-platform backup encryption using Python cryptography library
No external dependencies (GPG) required - works on Windows/Linux/Mac

Uses AES-256-GCM for encryption

⚠️  DEPRECATED: This is the old symmetric encryption format
Use AsymmetricBackupEncryption for new backups
Kept for backward compatibility only
"""
import os
import hashlib
import logging
from pathlib import Path
from typing import Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class BackupEncryption:
    """
    Encrypt/decrypt backups using AES-256-GCM
    
    ⚠️  DEPRECATED - Use AsymmetricBackupEncryption instead
    
    Features:
    - AES-256-GCM authenticated encryption
    - PBKDF2 key derivation (100,000 iterations)
    - Random salt per file
    - Nonce for each encryption
    - File format: [SALT:32][NONCE:12][ENCRYPTED_DATA][TAG:16]
    """
    
    SALT_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits (recommended for GCM)
    KEY_SIZE = 32  # 256 bits
    PBKDF2_ITERATIONS = 100000
    MAGIC_HEADER = b'PGBACKUP_AES256_V1'
    
    @classmethod
    def encrypt_file(cls, input_path: str, output_path: str, password: str) -> Dict:
        """
        Encrypt backup file with AES-256-GCM
        
        Args:
            input_path: Path to plaintext backup file
            output_path: Path for encrypted output (will add .encrypted extension)
            password: Encryption password
            
        Returns:
            {
                'status': 'success' | 'failed',
                'encrypted_path': '/path/to/file.backup.encrypted',
                'size': 12345678
            }
        """
        try:
            input_file = Path(input_path)
            
            if not input_file.exists():
                return {
                    'status': 'failed',
                    'error': f'Input file not found: {input_path}'
                }
            
            # Output path
            if not output_path:
                output_path = f"{input_path}.encrypted"
            
            output_file = Path(output_path)
            
            logger.info(f"Encrypting: {input_file.name} -> {output_file.name}")
            
            # Generate random salt
            salt = os.urandom(cls.SALT_SIZE)
            
            # Derive key from password using PBKDF2
            key = cls._derive_key(password, salt)
            
            # Generate random nonce
            nonce = os.urandom(cls.NONCE_SIZE)
            
            # Read plaintext data
            with open(input_file, 'rb') as f:
                plaintext = f.read()
            
            # Encrypt with AES-256-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            
            # Write encrypted file: [MAGIC][SALT][NONCE][CIPHERTEXT+TAG]
            with open(output_file, 'wb') as f:
                f.write(cls.MAGIC_HEADER)
                f.write(salt)
                f.write(nonce)
                f.write(ciphertext)
            
            output_size = output_file.stat().st_size
            
            logger.info(
                f"✓ Encrypted: {output_file.name}\n"
                f"  Original: {cls._format_size(input_file.stat().st_size)}\n"
                f"  Encrypted: {cls._format_size(output_size)}\n"
                f"  Algorithm: AES-256-GCM with PBKDF2"
            )
            
            return {
                'status': 'success',
                'encrypted_path': str(output_file),
                'size': output_size,
                'algorithm': 'AES-256-GCM'
            }
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    @classmethod
    def decrypt_file(cls, input_path: str, output_path: str, password: str) -> Dict:
        """
        Decrypt backup file
        
        Args:
            input_path: Path to encrypted file
            output_path: Path for decrypted output
            password: Decryption password
            
        Returns:
            {
                'status': 'success' | 'failed',
                'decrypted_path': '/path/to/file.backup',
                'size': 12345678
            }
        """
        try:
            input_file = Path(input_path)
            
            if not input_file.exists():
                return {
                    'status': 'failed',
                    'error': f'Encrypted file not found: {input_path}'
                }
            
            # Output path
            if not output_path:
                # Remove .encrypted extension or add .decrypted
                if input_path.endswith('.encrypted'):
                    output_path = input_path[:-10]  # Remove .encrypted
                else:
                    output_path = f"{input_path}.decrypted"
            
            output_file = Path(output_path)
            
            logger.info(f"Decrypting: {input_file.name}")
            
            # Read encrypted file
            with open(input_file, 'rb') as f:
                data = f.read()
            
            # Check magic header
            magic = data[:len(cls.MAGIC_HEADER)]
            if magic != cls.MAGIC_HEADER:
                return {
                    'status': 'failed',
                    'error': 'Invalid encrypted file format (missing magic header)'
                }
            
            # Extract components
            offset = len(cls.MAGIC_HEADER)
            salt = data[offset:offset + cls.SALT_SIZE]
            offset += cls.SALT_SIZE
            
            nonce = data[offset:offset + cls.NONCE_SIZE]
            offset += cls.NONCE_SIZE
            
            ciphertext = data[offset:]
            
            # Derive key from password
            key = cls._derive_key(password, salt)
            
            # Decrypt
            aesgcm = AESGCM(key)
            try:
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': f'Decryption failed - incorrect password or corrupted file: {e}'
                }
            
            # Write decrypted file
            with open(output_file, 'wb') as f:
                f.write(plaintext)
            
            output_size = output_file.stat().st_size
            
            logger.info(f"✓ Decrypted: {output_file.name} ({cls._format_size(output_size)})")
            
            return {
                'status': 'success',
                'decrypted_path': str(output_file),
                'size': output_size
            }
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    @classmethod
    def is_encrypted(cls, file_path: str) -> bool:
        """
        Check if file is encrypted with our format
        
        Args:
            file_path: Path to file
            
        Returns:
            True if encrypted, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(len(cls.MAGIC_HEADER))
                return magic == cls.MAGIC_HEADER
        except Exception:
            return False
    
    @classmethod
    def _derive_key(cls, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2-HMAC
        
        Args:
            password: User password
            salt: Random salt
            
        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=cls.KEY_SIZE,
            salt=salt,
            iterations=cls.PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode('utf-8'))
    
    @classmethod
    def _format_size(cls, size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
