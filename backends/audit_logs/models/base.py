# backends/audit_logs/models/base.py
"""
ABSTRACT BASE AUDIT LOG MODELS - For inheritance in study apps

These are ABSTRACT models - they don't create database tables directly.
Each study app should inherit from these and create their own migrations.

Usage in study app (e.g., study_43en/models/audit.py):
    from backends.audit_logs.models.base import AbstractAuditLog, AbstractAuditLogDetail
    
    class AuditLog(AbstractAuditLog):
        class Meta(AbstractAuditLog.Meta):
            app_label = 'study_43en'
            db_table = 'log"."audit_log'  # Or study-specific table
    
    class AuditLogDetail(AbstractAuditLogDetail):
        audit_log = models.ForeignKey(AuditLog, ...)
        class Meta(AbstractAuditLogDetail.Meta):
            app_label = 'study_43en'
"""
from django.db import models
from django.core.exceptions import PermissionDenied
from django.utils import timezone


class AbstractAuditLog(models.Model):
    """
    Abstract base audit log entry
    
    Inherit this in your study app and set proper app_label
    """
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('VIEW', 'View'),
    ]
    
    # WHO: User information
    user_id = models.IntegerField(
        db_index=True,
        help_text="User ID from management database"
    )
    
    username = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Username backup"
    )
    
    # WHEN: Timestamp
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # WHAT: Action details
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        db_index=True
    )
    
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="CRF model (e.g., SCREENINGCASE)"
    )
    
    patient_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Patient identifier (USUBJID or SCRID)"
    )
    
    SITEID = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_index=True,
        help_text="Site code for filtering"
    )
    
    # WHY: Reason
    reason = models.TextField(
        help_text="Combined change reason"
    )
    
    # METADATA: Context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    session_id = models.CharField(
        max_length=40,
        null=True,
        blank=True
    )
    
    # INTEGRITY: Checksum
    checksum = models.CharField(
        max_length=64,
        editable=False,
        help_text="SHA-256 checksum for integrity verification"
    )
    
    is_verified = models.BooleanField(
        default=True,
        help_text="Integrity status"
    )
    
    class Meta:
        abstract = True  # ← KEY: No database table for this model
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        default_permissions = ('add', 'view')
    
    def __str__(self):
        return f"{self.username} {self.action} {self.model_name} at {self.timestamp}"
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - audit logs are immutable"""
        raise PermissionDenied("Audit logs cannot be deleted")
    
    def save(self, *args, **kwargs):
        """Generate checksum and prevent editing"""
        if self.pk:
            raise PermissionDenied("Audit logs are immutable")
        
        if not self.checksum:
            from backends.audit_logs.utils.integrity import IntegrityChecker
            
            if hasattr(self, '_temp_checksum_data'):
                audit_data = self._temp_checksum_data.copy()
                audit_data['timestamp'] = str(self.timestamp)
            else:
                old_data = {}
                new_data = {}
                
                if hasattr(self, '_temp_details'):
                    for detail in self._temp_details:
                        field_name = detail['field_name']
                        old_data[field_name] = detail['old_value']
                        new_data[field_name] = detail['new_value']
                
                audit_data = {
                    'user_id': self.user_id,
                    'username': self.username,
                    'action': self.action,
                    'model_name': self.model_name,
                    'patient_id': self.patient_id,
                    'timestamp': str(self.timestamp),
                    'old_data': old_data,
                    'new_data': new_data,
                    'reason': self.reason,
                }
            
            self.checksum = IntegrityChecker.generate_checksum(audit_data)
        
        super().save(*args, **kwargs)
    
    def verify_integrity(self) -> bool:
        """Verify checksum integrity"""
        from backends.audit_logs.utils.integrity import IntegrityChecker
        
        details = self.details.all()
        
        old_data = {}
        new_data = {}
        
        for detail in details:
            old_data[detail.field_name] = detail.old_value
            new_data[detail.field_name] = detail.new_value
        
        audit_data = {
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'model_name': self.model_name,
            'patient_id': self.patient_id,
            'timestamp': str(self.timestamp),
            'old_data': old_data,
            'new_data': new_data,
            'reason': self.reason,
        }
        
        calculated_checksum = IntegrityChecker.generate_checksum(audit_data)
        return calculated_checksum == self.checksum
    
    def get_user(self):
        """Get user from management database"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.using('default').get(id=self.user_id)
        except:
            return None


class AbstractAuditLogDetail(models.Model):
    """
    Abstract base audit log detail
    
    NOTE: When inheriting, you must define the ForeignKey to your concrete AuditLog:
    
        class AuditLogDetail(AbstractAuditLogDetail):
            audit_log = models.ForeignKey(
                'AuditLog',  # Your concrete model
                on_delete=models.PROTECT,
                related_name='details'
            )
    """
    
    # NOTE: audit_log FK must be defined in concrete class
    
    field_name = models.CharField(
        max_length=100,
        help_text="Technical field name"
    )
    
    old_value = models.TextField(
        null=True,
        blank=True,
        help_text="Old value (as string)"
    )
    
    new_value = models.TextField(
        null=True,
        blank=True,
        help_text="New value (as string)"
    )
    
    reason = models.TextField(
        help_text="Reason for this specific field change"
    )
    
    class Meta:
        abstract = True  # ← KEY: No database table for this model
        ordering = ['field_name']
        verbose_name = 'Audit Log Detail'
        verbose_name_plural = 'Audit Log Details'
        default_permissions = ('add', 'view')
    
    def __str__(self):
        return f"{self.field_name}: {self.old_value} → {self.new_value}"
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - audit logs are immutable"""
        raise PermissionDenied("Audit log details cannot be deleted")
    
    def save(self, *args, **kwargs):
        """Prevent editing"""
        if self.pk:
            raise PermissionDenied("Audit log details are immutable")
        super().save(*args, **kwargs)
