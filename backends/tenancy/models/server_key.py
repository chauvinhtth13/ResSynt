"""
Server RSA Key Storage Model

Stores server's RSA key pair for encrypting/decrypting backup session keys
"""
from django.db import models
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ServerKey(models.Model):
    """
    Server RSA Key Pair Storage
    
    Stores:
    - Private key: Encrypted with FIELD_ENCRYPTION_KEY (or password)
    - Public key: Plain text (can be public)
    - Metadata: Key size, fingerprint, rotation info
    
    Only one active server key pair exists at a time
    """
    
    # Key data (PEM format)
    private_key_pem = models.TextField(
        help_text="RSA private key (encrypted PEM format)"
    )
    public_key_pem = models.TextField(
        help_text="RSA public key (PEM format)"
    )
    
    # Key metadata
    key_size = models.IntegerField(
        default=4096,
        help_text="RSA key size in bits"
    )
    fingerprint = models.CharField(
        max_length=100,
        help_text="SHA-256 fingerprint of public key"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is this the active server key pair?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When key was generated"
    )
    rotated_from = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rotated_to',
        help_text="Previous key (if this is a rotation)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Admin notes about this key"
    )
    
    class Meta:
        db_table = 'tenancy_server_key'
        verbose_name = "Server RSA Key"
        verbose_name_plural = "Server RSA Keys"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"Server Key {self.fingerprint[:16]}... ({status})"
    
    @classmethod
    def get_active_key(cls):
        """
        Get the active server key pair
        
        Returns:
            ServerKey instance or None
        """
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            logger.warning("No active server key found")
            return None
        except cls.MultipleObjectsReturned:
            logger.error("Multiple active server keys found! Using most recent.")
            return cls.objects.filter(is_active=True).first()
    
    @classmethod
    def deactivate_all(cls):
        """Deactivate all server keys"""
        cls.objects.update(is_active=False)
        logger.info("All server keys deactivated")
    
    def deactivate(self):
        """Deactivate this key"""
        self.is_active = False
        self.save(update_fields=['is_active'])
        logger.info(f"Server key {self.fingerprint[:16]}... deactivated")
    
    def activate(self):
        """
        Activate this key (deactivates all others)
        """
        # Deactivate all other keys
        ServerKey.objects.exclude(pk=self.pk).update(is_active=False)
        
        # Activate this one
        self.is_active = True
        self.save(update_fields=['is_active'])
        
        logger.info(f"Server key {self.fingerprint[:16]}... activated")
    
    def get_private_key(self, password: str):
        """
        Decrypt and return private key object
        
        Args:
            password: Password to decrypt private key
            
        Returns:
            RSAPrivateKey object
        """
        from backends.tenancy.utils.key_manager import KeyManager
        
        return KeyManager.load_private_key(
            self.private_key_pem.encode('utf-8'),
            password
        )
    
    def get_public_key(self):
        """
        Return public key object
        
        Returns:
            RSAPublicKey object
        """
        from backends.tenancy.utils.key_manager import KeyManager
        
        return KeyManager.load_public_key(
            self.public_key_pem.encode('utf-8')
        )
