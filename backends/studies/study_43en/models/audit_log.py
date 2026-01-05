# backends/studies/study_43en/models/audit_log.py
"""
 FIXED: Audit Log Models - Schema handled by schema_editor
"""
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from backends.studies.study_43en.study_site_manage import SiteFilteredManager

class AuditLog(models.Model):
    """
    Main audit log entry
     Schema routing handled automatically by schema_editor
    """

    objects = models.Manager()
    site_objects = SiteFilteredManager()
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('VIEW', 'View'),
    ]
    
    # WHO
    user_id = models.IntegerField(
        db_index=True,
        help_text="User ID from management database"
    )
    
    username = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Username backup"
    )
    
    # WHEN
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # WHAT
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
        help_text="Patient identifier"
    )
    
    SITEID = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_index=True
    )
    
    # WHY
    reason = models.TextField(
        help_text="Combined change reason"
    )
    
    # METADATA
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    session_id = models.CharField(
        max_length=40,
        null=True,
        blank=True
    )
    
    # INTEGRITY
    checksum = models.CharField(
        max_length=64,
        editable=False
    )
    
    is_verified = models.BooleanField(default=True)
    
    class Meta:
        #  CHANGED: No schema prefix - let schema_editor handle it
        db_table = 'audit_log'  # Simple table name
        
        #  ADD: Mark this as audit log table using db_table_comment
        db_table_comment = 'AUDIT_LOG_TABLE'  # Special marker
        
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        
        default_permissions = ('add', 'view')
        
        indexes = [
            models.Index(fields=['-timestamp'], name='audit_log_time_idx'),
            models.Index(fields=['patient_id', '-timestamp'], name='audit_log_patient_idx'),
            models.Index(fields=['user_id', '-timestamp'], name='audit_log_user_idx'),
            models.Index(fields=['SITEID', '-timestamp'], name='audit_log_site_idx'),
            models.Index(fields=['model_name', 'action'], name='audit_log_model_idx'),
        ]
    
    def __str__(self):
        return f"{self.username} {self.action} {self.model_name} at {self.timestamp}"
    
    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit logs cannot be deleted")
    
    def save(self, *args, **kwargs):
        """Generate checksum if not exists"""
        if self.pk:
            raise PermissionDenied("Audit logs are immutable")
        
        if not self.checksum:
            # ✅ NEW: Import from base audit_log
            from backends.audit_log.utils.integrity import IntegrityChecker
            
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
        """Verify checksum"""
        # ✅ NEW: Import from base audit_log
        from backends.audit_log.utils.integrity import IntegrityChecker
        
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
        is_valid = (calculated_checksum == self.checksum)
        
        if not is_valid:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f" INTEGRITY VIOLATION: AuditLog {self.id} checksum mismatch!\n"
                f"   Expected: {calculated_checksum}\n"
                f"   Stored:   {self.checksum}"
            )
        
        return is_valid
    
    def get_user(self):
        """Get user from management database"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.using('default').get(id=self.user_id)
        except:
            return None


class AuditLogDetail(models.Model):
    """
    Field-level change details
     Schema routing handled automatically by schema_editor
    """
    
    audit_log = models.ForeignKey(
        AuditLog,
        on_delete=models.PROTECT,
        related_name='details'
    )
    
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
        #  CHANGED: No schema prefix
        db_table = 'audit_log_detail'
        
        #  ADD: Mark as audit log table
        db_table_comment = 'AUDIT_LOG_TABLE'
        
        ordering = ['field_name']
        verbose_name = 'Audit Log Detail'
        verbose_name_plural = 'Audit Log Details'
        
        default_permissions = ('add', 'view')
        
        indexes = [
            models.Index(fields=['audit_log', 'field_name'], name='audit_detail_log_idx'),
        ]
    
    def __str__(self):
        return f"{self.field_name}: {self.old_value} → {self.new_value}"
    
    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit log details cannot be deleted")
    
    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionDenied("Audit log details are immutable")
        super().save(*args, **kwargs)