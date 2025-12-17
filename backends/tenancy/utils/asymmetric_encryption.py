"""
Asymmetric Backup Encryption using RSA + AES Hybrid

This module implements hybrid encryption for database backups:
- RSA-4096 for key encryption and digital signatures
- AES-256-GCM for data encryption
- Backward compatible with symmetric encryption format

ENCRYPTION FLOW:
1. Generate random AES-256 session key
2. Encrypt backup data with session key (AES-GCM)
3. Calculate SHA-256 hash of encrypted data
4. Sign hash with User's RSA private key (RSA-PSS)
5. Encrypt session key with Server's RSA public key (RSA-OAEP)
6. Output: [Metadata][Encrypted Session Key][Signature][Encrypted Data]

DECRYPTION FLOW:
1. Decrypt session key with Server's RSA private key
2. Decrypt data with session key
3. Verify signature with User's RSA public key
4. Return decrypted data
"""
import os
import struct
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class AsymmetricBackupEncryption:
    """
    Hybrid RSA + AES encryption for backups
    
    File Format:
    [MAGIC_HEADER:20]        # "PGBACKUP_HYBRID_V1\x00\x00"
    [VERSION:4]              # Version number (uint32)
    [USER_ID:8]              # User ID who created backup (uint64)
    [TIMESTAMP:8]            # Unix timestamp (uint64)
    [ENCRYPTED_KEY_SIZE:4]   # Size of encrypted session key (uint32)
    [ENCRYPTED_KEY:N]        # RSA-encrypted session key
    [SIGNATURE_SIZE:4]       # Size of signature (uint32)
    [SIGNATURE:M]            # RSA-PSS signature
    [NONCE:12]               # AES-GCM nonce
    [ENCRYPTED_DATA:...]     # AES-GCM encrypted data + auth tag
    """
    
    MAGIC_HEADER = b'PGBACKUP_HYBRID_V1\x00\x00'
    VERSION = 1
    NONCE_SIZE = 12
    SESSION_KEY_SIZE = 32  # AES-256
    
    # Old symmetric format magic (for backward compatibility)
    OLD_MAGIC_HEADER = b'PGBACKUP_AES256_V1'
    
    @classmethod
    def encrypt_file(
        cls,
        input_path: str,
        user,
        server_public_key: 'rsa.RSAPublicKey',
        user_private_key: 'rsa.RSAPrivateKey',
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Encrypt backup file with hybrid encryption
        
        Args:
            input_path: Path to plaintext backup file
            user: User object (Django User model)
            server_public_key: Server's RSA public key
            user_private_key: User's RSA private key (for signing)
            output_path: Path for encrypted output (default: input_path + .encrypted)
            
        Returns:
            {
                'status': 'success' | 'failed',
                'encrypted_path': '/path/to/file.backup.encrypted',
                'size': 12345678,
                'algorithm': 'RSA-4096 + AES-256-GCM'
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
            
            logger.info(f"🔐 Encrypting: {input_file.name}")
            logger.info(f"   User: {user.username} (ID: {user.id})")
            
            # 1. Read plaintext data
            with open(input_file, 'rb') as f:
                plaintext = f.read()
            
            plaintext_size = len(plaintext)
            logger.info(f"   Input size: {cls._format_size(plaintext_size)}")
            
            # 2. Generate random session key (AES-256)
            session_key = os.urandom(cls.SESSION_KEY_SIZE)
            
            # 3. Generate random nonce for AES-GCM
            nonce = os.urandom(cls.NONCE_SIZE)
            
            # 4. Encrypt data with session key (AES-256-GCM)
            aesgcm = AESGCM(session_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            
            # 5. Calculate hash of encrypted data
            data_hash = hashlib.sha256(ciphertext).digest()
            
            # 6. Sign hash with User's private key (RSA-PSS)
            signature = user_private_key.sign(
                data_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            logger.info(f"   ✓ Signature created (RSA-PSS)")
            
            # 7. Encrypt session key with Server's public key (RSA-OAEP)
            encrypted_session_key = server_public_key.encrypt(
                session_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            logger.info(f"   ✓ Session key encrypted (RSA-OAEP)")
            
            # 8. Build encrypted file
            timestamp = int(datetime.now().timestamp())
            
            with open(output_file, 'wb') as f:
                # Header
                f.write(cls.MAGIC_HEADER)
                f.write(struct.pack('<I', cls.VERSION))
                f.write(struct.pack('<Q', user.id))
                f.write(struct.pack('<Q', timestamp))
                
                # Encrypted session key
                f.write(struct.pack('<I', len(encrypted_session_key)))
                f.write(encrypted_session_key)
                
                # Signature
                f.write(struct.pack('<I', len(signature)))
                f.write(signature)
                
                # Nonce + encrypted data
                f.write(nonce)
                f.write(ciphertext)
            
            output_size = output_file.stat().st_size
            
            logger.info(
                f"✓ Encrypted: {output_file.name}\n"
                f"  Original: {cls._format_size(plaintext_size)}\n"
                f"  Encrypted: {cls._format_size(output_size)}\n"
                f"  Algorithm: RSA-4096 + AES-256-GCM\n"
                f"  Signed by: {user.username}"
            )
            
            return {
                'status': 'success',
                'encrypted_path': str(output_file),
                'size': output_size,
                'algorithm': 'RSA-4096 + AES-256-GCM',
                'user_id': user.id,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    @classmethod
    def decrypt_file(
        cls,
        input_path: str,
        server_private_key: 'rsa.RSAPrivateKey',
        user_public_key: Optional['rsa.RSAPublicKey'] = None,
        output_path: Optional[str] = None,
        verify_signature: bool = True
    ) -> Dict:
        """
        Decrypt backup file and verify signature
        
        Args:
            input_path: Path to encrypted file
            server_private_key: Server's RSA private key
            user_public_key: User's RSA public key (for signature verification)
            output_path: Path for decrypted output
            verify_signature: Whether to verify signature (default: True)
            
        Returns:
            {
                'status': 'success' | 'failed',
                'decrypted_path': '/path/to/file.backup',
                'size': 12345678,
                'user_id': 123,
                'timestamp': 1734345600,
                'signature_valid': True
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
                if input_path.endswith('.encrypted'):
                    output_path = input_path[:-10]
                else:
                    output_path = f"{input_path}.decrypted"
            output_file = Path(output_path)
            
            logger.info(f"🔓 Decrypting: {input_file.name}")
            
            # Read encrypted file
            with open(input_file, 'rb') as f:
                data = f.read()
            
            # Check format
            if not cls.is_hybrid_encrypted(input_path):
                return {
                    'status': 'failed',
                    'error': 'Not a hybrid encrypted file (use old decryption method)'
                }
            
            # Parse file structure
            offset = len(cls.MAGIC_HEADER)
            
            # Version
            version = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # User ID
            user_id = struct.unpack('<Q', data[offset:offset+8])[0]
            offset += 8
            
            # Timestamp
            timestamp = struct.unpack('<Q', data[offset:offset+8])[0]
            offset += 8
            
            logger.info(f"   Creator ID: {user_id}")
            logger.info(f"   Created: {datetime.fromtimestamp(timestamp)}")
            
            # Encrypted session key
            encrypted_key_size = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            encrypted_session_key = data[offset:offset+encrypted_key_size]
            offset += encrypted_key_size
            
            # Signature
            signature_size = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            signature = data[offset:offset+signature_size]
            offset += signature_size
            
            # Nonce
            nonce = data[offset:offset+cls.NONCE_SIZE]
            offset += cls.NONCE_SIZE
            
            # Encrypted data
            ciphertext = data[offset:]
            
            # Decrypt session key with Server's private key
            try:
                session_key = server_private_key.decrypt(
                    encrypted_session_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                logger.info("   ✓ Session key decrypted")
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': f'Failed to decrypt session key: {e}'
                }
            
            # Verify signature (if requested and public key provided)
            signature_valid = None
            if verify_signature and user_public_key:
                data_hash = hashlib.sha256(ciphertext).digest()
                
                try:
                    user_public_key.verify(
                        signature,
                        data_hash,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    signature_valid = True
                    logger.info("   ✓ Signature verified")
                except Exception as e:
                    signature_valid = False
                    logger.warning(f"   ✗ Signature verification failed: {e}")
                    
                    if verify_signature:
                        return {
                            'status': 'failed',
                            'error': 'Signature verification failed - file may be tampered',
                            'signature_valid': False
                        }
            
            # Decrypt data with session key
            try:
                aesgcm = AESGCM(session_key)
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
                logger.info("   ✓ Data decrypted")
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': f'Failed to decrypt data: {e}'
                }
            
            # Write decrypted file
            with open(output_file, 'wb') as f:
                f.write(plaintext)
            
            output_size = output_file.stat().st_size
            
            logger.info(f"✓ Decrypted: {output_file.name} ({cls._format_size(output_size)})")
            
            return {
                'status': 'success',
                'decrypted_path': str(output_file),
                'size': output_size,
                'user_id': user_id,
                'timestamp': timestamp,
                'signature_valid': signature_valid
            }
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    @classmethod
    def is_hybrid_encrypted(cls, file_path: str) -> bool:
        """
        Check if file is encrypted with hybrid format
        
        Args:
            file_path: Path to file
            
        Returns:
            True if hybrid encrypted, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(len(cls.MAGIC_HEADER))
                return magic == cls.MAGIC_HEADER
        except Exception:
            return False
    
    @classmethod
    def is_symmetric_encrypted(cls, file_path: str) -> bool:
        """
        Check if file is encrypted with old symmetric format
        
        Args:
            file_path: Path to file
            
        Returns:
            True if symmetric encrypted, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(len(cls.OLD_MAGIC_HEADER))
                return magic == cls.OLD_MAGIC_HEADER
        except Exception:
            return False
    
    @classmethod
    def get_file_metadata(cls, file_path: str) -> Optional[Dict]:
        """
        Extract metadata from encrypted file without decrypting
        
        Args:
            file_path: Path to encrypted file
            
        Returns:
            {
                'format': 'hybrid',
                'version': 1,
                'user_id': 123,
                'timestamp': 1734345600,
                'created': '2024-12-16 10:00:00'
            } or None
        """
        try:
            if not cls.is_hybrid_encrypted(file_path):
                return None
            
            with open(file_path, 'rb') as f:
                data = f.read(len(cls.MAGIC_HEADER) + 4 + 8 + 8)
            
            offset = len(cls.MAGIC_HEADER)
            version = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            user_id = struct.unpack('<Q', data[offset:offset+8])[0]
            offset += 8
            timestamp = struct.unpack('<Q', data[offset:offset+8])[0]
            
            return {
                'format': 'hybrid',
                'version': version,
                'user_id': user_id,
                'timestamp': timestamp,
                'created': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            return None
    
    @classmethod
    def _format_size(cls, size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


# Keep old BackupEncryption class for backward compatibility
from backends.tenancy.utils.backup_encryption import BackupEncryption as SymmetricBackupEncryption

__all__ = ['AsymmetricBackupEncryption', 'SymmetricBackupEncryption']
