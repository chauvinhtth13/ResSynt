# backends/audit_log/models/audit_log.py
"""
🌐 BASE AUDIT LOG MODELS - Shared across all studies

Features:
- Schema-aware (works with multi-schema PostgreSQL)
- Immutable audit logs (cannot edit/delete)
- Checksum-based integrity verification
- Site-based access control
- Cross-study compatible

Usage in studies:
    from backends.audit_log.models import AuditLog, AuditLogDetail
"""
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import PermissionDenied
from django.utils import timezone

class AuditLog(models.Model):
    """
    Main audit log entry - BASE MODEL for all studies
    
    🔄 Schema routing handled automatically by schema_editor
    """
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('VIEW', 'View'),
    ]
    
    # ==========================================
    # WHO: User information
    # ==========================================
    user_id = models.IntegerField(
        db_index=True,
        help_text="User ID from management database"
    )
    
    username = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Username backup"
    )
    
    # ==========================================
    # WHEN: Timestamp
    # ==========================================
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # ==========================================
    # WHAT: Action details
    # ==========================================
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
    
    # ==========================================
    # WHY: Reason
    # ==========================================
    reason = models.TextField(
        help_text="Combined change reason"
    )
    
    # ==========================================
    # METADATA: Context
    # ==========================================
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    session_id = models.CharField(
        max_length=40,
        null=True,
        blank=True
    )
    
    # ==========================================
    # INTEGRITY: Checksum
    # ==========================================
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
        # 🌐 IMPORTANT: Use 'log' schema prefix for audit tables
        db_table = 'log"."audit_log'
        
        # 🔧 Mark this as audit log table using db_table_comment
        db_table_comment = 'AUDIT_LOG_TABLE'  # Special marker for schema_editor
        
        # ✅ CRITICAL: Declare app_label for base models
        app_label = 'audit_log'
        
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
        """🔒 Prevent deletion - audit logs are immutable"""
        raise PermissionDenied("Audit logs cannot be deleted")
    
    def save(self, *args, **kwargs):
        """
        🔒 Generate checksum and prevent editing
        
        Checksum is generated from:
        - User info (user_id, username)
        - Action details (action, model_name, patient_id, timestamp)
        - Change data (old_data, new_data)
        - Reason
        """
        if self.pk:
            raise PermissionDenied("Audit logs are immutable")
        
        if not self.checksum:
            from backends.audit_log.utils.integrity import IntegrityChecker
            
            # Use temp data if available (set by decorator)
            if hasattr(self, '_temp_checksum_data'):
                audit_data = self._temp_checksum_data.copy()
                audit_data['timestamp'] = str(self.timestamp)
            else:
                # Fallback: build from details
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
        """
        🔍 Verify checksum integrity
        
        Returns:
            bool: True if checksum matches, False if tampered
        """
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
                f"🚨 INTEGRITY VIOLATION: AuditLog {self.id} checksum mismatch!\n"
                f"   Expected: {calculated_checksum}\n"
                f"   Stored:   {self.checksum}"
            )
        
        return is_valid
    
    def get_user(self):
        """
        Get user from management database
        
        Returns:
            User instance or None
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.using('default').get(id=self.user_id)
        except:
            return None


class AuditLogDetail(models.Model):
    """
    Field-level change details - BASE MODEL for all studies
    
    🔄 Schema routing handled automatically by schema_editor
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
        # 🌐 IMPORTANT: Use 'log' schema prefix for audit tables
        db_table = 'log"."audit_log_detail'
        
        # 🔧 Mark as audit log table
        db_table_comment = 'AUDIT_LOG_TABLE'
        
        # ✅ CRITICAL: Declare app_label for base models
        app_label = 'audit_log'
        
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
        """🔒 Prevent deletion - audit logs are immutable"""
        raise PermissionDenied("Audit log details cannot be deleted")
    
    def save(self, *args, **kwargs):
        """🔒 Prevent editing"""
        if self.pk:
            raise PermissionDenied("Audit log details are immutable")
        super().save(*args, **kwargs)
