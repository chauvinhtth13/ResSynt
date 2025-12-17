"""
RSA Key Management for Asymmetric Backup Encryption

Handles generation, storage, and loading of RSA key pairs for:
- Server keys (encrypt session keys)
- User keys (sign backups)
"""
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Base class for RSA key management
    
    Features:
    - Generate RSA-4096 key pairs
    - Export to PEM format (encrypted private, plain public)
    - Load from PEM format
    - Key validation
    """
    
    DEFAULT_KEY_SIZE = 4096
    PBKDF2_ITERATIONS = 100000
    
    @classmethod
    def generate_key_pair(
        cls, 
        key_size: int = DEFAULT_KEY_SIZE
    ) -> Tuple['rsa.RSAPrivateKey', 'rsa.RSAPublicKey']:
        """
        Generate RSA key pair
        
        Args:
            key_size: Key size in bits (default: 4096)
            
        Returns:
            (private_key, public_key) tuple
        """
        logger.info(f"Generating RSA-{key_size} key pair...")
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        logger.info("✓ Key pair generated successfully")
        
        return private_key, public_key
    
    @classmethod
    def export_private_key(
        cls,
        private_key: 'rsa.RSAPrivateKey',
        password: str
    ) -> bytes:
        """
        Export private key to encrypted PEM format
        
        Args:
            private_key: RSA private key object
            password: Encryption password
            
        Returns:
            Encrypted PEM bytes
        """
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                password.encode('utf-8')
            )
        )
        
        logger.debug("Private key exported (encrypted)")
        return pem
    
    @classmethod
    def export_private_key_unencrypted(
        cls,
        private_key: 'rsa.RSAPrivateKey'
    ) -> bytes:
        """
        Export private key to unencrypted PEM format
        
        WARNING: Only use for testing or when storing in secure encrypted storage
        
        Args:
            private_key: RSA private key object
            
        Returns:
            Unencrypted PEM bytes
        """
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        logger.warning("Private key exported WITHOUT encryption")
        return pem
    
    @classmethod
    def export_public_key(
        cls,
        public_key: 'rsa.RSAPublicKey'
    ) -> bytes:
        """
        Export public key to PEM format
        
        Args:
            public_key: RSA public key object
            
        Returns:
            PEM bytes
        """
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        logger.debug("Public key exported")
        return pem
    
    @classmethod
    def load_private_key(
        cls,
        pem_data: bytes,
        password: Optional[str] = None
    ) -> 'rsa.RSAPrivateKey':
        """
        Load private key from PEM format
        
        Args:
            pem_data: PEM bytes
            password: Decryption password (if encrypted)
            
        Returns:
            RSA private key object
        """
        password_bytes = password.encode('utf-8') if password else None
        
        private_key = serialization.load_pem_private_key(
            pem_data,
            password=password_bytes,
            backend=default_backend()
        )
        
        logger.debug("Private key loaded")
        return private_key
    
    @classmethod
    def load_public_key(
        cls,
        pem_data: bytes
    ) -> 'rsa.RSAPublicKey':
        """
        Load public key from PEM format
        
        Args:
            pem_data: PEM bytes
            
        Returns:
            RSA public key object
        """
        public_key = serialization.load_pem_public_key(
            pem_data,
            backend=default_backend()
        )
        
        logger.debug("Public key loaded")
        return public_key
    
    @classmethod
    def validate_key_pair(
        cls,
        private_key: 'rsa.RSAPrivateKey',
        public_key: 'rsa.RSAPublicKey'
    ) -> bool:
        """
        Validate that private and public keys match
        
        Args:
            private_key: RSA private key
            public_key: RSA public key
            
        Returns:
            True if keys match, False otherwise
        """
        try:
            # Test encryption/decryption
            test_message = b"test_key_validation"
            
            # Encrypt with public key
            ciphertext = public_key.encrypt(
                test_message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt with private key
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return plaintext == test_message
            
        except Exception as e:
            logger.error(f"Key validation failed: {e}")
            return False


class ServerKeyManager(KeyManager):
    """
    Manage Server RSA keys for encrypting session keys
    
    Server keys are used to:
    - Encrypt AES session keys (RSA-OAEP)
    - Decrypt session keys during backup restoration
    """
    
    @classmethod
    def get_key_info(cls, public_key: 'rsa.RSAPublicKey') -> Dict:
        """
        Get information about public key
        
        Args:
            public_key: RSA public key
            
        Returns:
            {
                'key_size': 4096,
                'public_exponent': 65537,
                'fingerprint': 'SHA256:abc123...'
            }
        """
        key_size = public_key.key_size
        public_numbers = public_key.public_numbers()
        
        # Calculate fingerprint
        pem = cls.export_public_key(public_key)
        fingerprint = cls._calculate_fingerprint(pem)
        
        return {
            'key_size': key_size,
            'public_exponent': public_numbers.e,
            'fingerprint': fingerprint
        }
    
    @classmethod
    def _calculate_fingerprint(cls, pem_data: bytes) -> str:
        """
        Calculate SHA-256 fingerprint of key
        
        Args:
            pem_data: PEM bytes
            
        Returns:
            Fingerprint string (format: SHA256:hexdigest)
        """
        from hashlib import sha256
        digest = sha256(pem_data).hexdigest()
        return f"SHA256:{digest[:32]}..."


class UserKeyManager(KeyManager):
    """
    Manage User RSA keys for signing backups
    
    User keys are used to:
    - Sign backup data (RSA-PSS signature)
    - Verify backup authenticity and integrity
    """
    
    @classmethod
    def create_user_keypair(
        cls,
        user_identifier: str,
        password: str,
        key_size: int = KeyManager.DEFAULT_KEY_SIZE
    ) -> Dict:
        """
        Create key pair for user
        
        Args:
            user_identifier: Username or user ID
            password: Password to encrypt private key
            key_size: Key size in bits
            
        Returns:
            {
                'private_key_pem': bytes,
                'public_key_pem': bytes,
                'fingerprint': str,
                'created_at': datetime
            }
        """
        logger.info(f"Creating key pair for user: {user_identifier}")
        
        # Generate keys
        private_key, public_key = cls.generate_key_pair(key_size)
        
        # Export
        private_pem = cls.export_private_key(private_key, password)
        public_pem = cls.export_public_key(public_key)
        
        # Fingerprint
        fingerprint = ServerKeyManager._calculate_fingerprint(public_pem)
        
        return {
            'private_key_pem': private_pem,
            'public_key_pem': public_pem,
            'fingerprint': fingerprint,
            'created_at': datetime.now(),
            'key_size': key_size
        }
    
    @classmethod
    def rotate_user_key(
        cls,
        user_identifier: str,
        old_password: str,
        new_password: str,
        old_private_pem: bytes
    ) -> Dict:
        """
        Rotate user key (generate new pair)
        
        Args:
            user_identifier: Username
            old_password: Old private key password
            new_password: New private key password
            old_private_pem: Old private key PEM
            
        Returns:
            New key pair dict (same format as create_user_keypair)
        """
        logger.info(f"Rotating key for user: {user_identifier}")
        
        # Verify old key can be decrypted
        try:
            old_private_key = cls.load_private_key(old_private_pem, old_password)
            logger.info("✓ Old key verified")
        except Exception as e:
            raise ValueError(f"Cannot decrypt old private key: {e}")
        
        # Generate new key pair
        return cls.create_user_keypair(user_identifier, new_password)


class FileKeyStorage:
    """
    File-based key storage (for testing and simple deployments)
    
    Production should use database storage with encryption
    """
    
    def __init__(self, storage_dir: Path):
        """
        Initialize file storage
        
        Args:
            storage_dir: Directory to store keys
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File key storage: {self.storage_dir}")
    
    def save_server_keys(
        self,
        private_key: 'rsa.RSAPrivateKey',
        public_key: 'rsa.RSAPublicKey',
        password: str
    ):
        """
        Save server key pair to files
        
        Args:
            private_key: RSA private key
            public_key: RSA public key
            password: Password to encrypt private key
        """
        # Export
        private_pem = KeyManager.export_private_key(private_key, password)
        public_pem = KeyManager.export_public_key(public_key)
        
        # Save
        private_file = self.storage_dir / 'server_private_key.pem'
        public_file = self.storage_dir / 'server_public_key.pem'
        
        private_file.write_bytes(private_pem)
        public_file.write_bytes(public_pem)
        
        # Secure permissions on Unix
        if os.name != 'nt':
            os.chmod(private_file, 0o600)
            os.chmod(public_file, 0o644)
        
        logger.info(f"✓ Server keys saved to {self.storage_dir}")
    
    def load_server_keys(
        self,
        password: str
    ) -> Tuple['rsa.RSAPrivateKey', 'rsa.RSAPublicKey']:
        """
        Load server key pair from files
        
        Args:
            password: Password to decrypt private key
            
        Returns:
            (private_key, public_key) tuple
        """
        private_file = self.storage_dir / 'server_private_key.pem'
        public_file = self.storage_dir / 'server_public_key.pem'
        
        if not private_file.exists() or not public_file.exists():
            raise FileNotFoundError("Server keys not found")
        
        private_pem = private_file.read_bytes()
        public_pem = public_file.read_bytes()
        
        private_key = KeyManager.load_private_key(private_pem, password)
        public_key = KeyManager.load_public_key(public_pem)
        
        logger.info("✓ Server keys loaded")
        return private_key, public_key
    
    def server_keys_exist(self) -> bool:
        """Check if server keys exist"""
        private_file = self.storage_dir / 'server_private_key.pem'
        public_file = self.storage_dir / 'server_public_key.pem'
        return private_file.exists() and public_file.exists()
