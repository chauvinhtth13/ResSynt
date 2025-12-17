"""
Encryption Audit Log Model

Tracks all encryption/decryption operations for security monitoring
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class EncryptionAuditLog(models.Model):
    """
    Audit log for encryption operations
    
    Tracks:
    - All encrypt/decrypt/verify operations
    - User who performed the action
    - Backup file involved
    - Success/failure status
    - Signature verification results
    """
    
    ACTION_ENCRYPT = 'ENCRYPT'
    ACTION_DECRYPT = 'DECRYPT'
    ACTION_VERIFY = 'VERIFY'
    ACTION_KEY_GEN = 'KEY_GEN'
    ACTION_KEY_ROTATE = 'KEY_ROTATE'
    
    ACTION_CHOICES = [
        (ACTION_ENCRYPT, 'Encrypted'),
        (ACTION_DECRYPT, 'Decrypted'),
        (ACTION_VERIFY, 'Verified'),
        (ACTION_KEY_GEN, 'Key Generated'),
        (ACTION_KEY_ROTATE, 'Key Rotated'),
    ]
    
    # Action info
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True
    )
    
    # User who performed action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encryption_actions'
    )
    
    # Backup creator (if different from user)
    backup_creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backups_created'
    )
    
    # Backup file
    backup_file = models.CharField(
        max_length=500,
        help_text="Backup file path"
    )
    
    # Results
    success = models.BooleanField(
        default=True,
        help_text="Operation succeeded?"
    )
    signature_valid = models.BooleanField(
        null=True,
        blank=True,
        help_text="Was signature valid? (for decrypt/verify)"
    )
    
    # Metadata
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of requester"
    )
    
    # Additional details (JSON)
    details = models.JSONField(
        default=dict,
        help_text="Additional operation details (error messages, file sizes, etc.)"
    )
    
    class Meta:
        db_table = 'tenancy_encryption_audit_log'
        verbose_name = "Encryption Audit Log"
        verbose_name_plural = "Encryption Audit Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{self.action} by {user_str} at {self.timestamp}"
    
    @classmethod
    def log_encrypt(cls, user, backup_file, success=True, details=None):
        """Log encryption operation"""
        return cls.objects.create(
            action=cls.ACTION_ENCRYPT,
            user=user,
            backup_creator=user,
            backup_file=backup_file,
            success=success,
            details=details or {}
        )
    
    @classmethod
    def log_decrypt(cls, user, backup_file, backup_creator=None, 
                    signature_valid=None, success=True, details=None, ip_address=None):
        """Log decryption operation"""
        return cls.objects.create(
            action=cls.ACTION_DECRYPT,
            user=user,
            backup_creator=backup_creator,
            backup_file=backup_file,
            success=success,
            signature_valid=signature_valid,
            ip_address=ip_address,
            details=details or {}
        )
    
    @classmethod
    def log_verify(cls, user, backup_file, backup_creator=None,
                   signature_valid=None, success=True, details=None):
        """Log verification operation"""
        return cls.objects.create(
            action=cls.ACTION_VERIFY,
            user=user,
            backup_creator=backup_creator,
            backup_file=backup_file,
            success=success,
            signature_valid=signature_valid,
            details=details or {}
        )
    
    @classmethod
    def log_key_generation(cls, user, details=None):
        """Log key generation"""
        return cls.objects.create(
            action=cls.ACTION_KEY_GEN,
            user=user,
            backup_file='',
            success=True,
            details=details or {}
        )
    
    @classmethod
    def log_key_rotation(cls, user, details=None):
        """Log key rotation"""
        return cls.objects.create(
            action=cls.ACTION_KEY_ROTATE,
            user=user,
            backup_file='',
            success=True,
            details=details or {}
        )
    
    @classmethod
    def get_failed_attempts(cls, hours=24):
        """
        Get failed operations in last N hours
        
        Returns:
            QuerySet of failed operations
        """
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        
        return cls.objects.filter(
            success=False,
            timestamp__gte=cutoff
        )
    
    @classmethod
    def get_invalid_signatures(cls, hours=24):
        """
        Get invalid signature attempts in last N hours
        
        Returns:
            QuerySet of invalid signature attempts
        """
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        
        return cls.objects.filter(
            signature_valid=False,
            timestamp__gte=cutoff
        )
