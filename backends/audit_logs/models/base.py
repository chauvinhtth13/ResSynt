# backends/audit_logs/models/base.py
"""
ABSTRACT AUDIT LOG MODELS + FACTORY FUNCTION

This module provides:
1. Abstract base models (AbstractAuditLog, AbstractAuditLogDetail)
2. Factory function to create concrete models for each study

Database Schema Structure:
- Each study database has 2 schemas: 'data' (CRF tables) and 'logging' (audit tables)
- Audit tables: logging.audit_log, logging.audit_log_detail

Usage in study app (e.g., study_43en/models/__init__.py):
    from backends.audit_logs.models.base import create_audit_models
    
    # Create concrete AuditLog and AuditLogDetail for this study
    AuditLog, AuditLogDetail = create_audit_models('study_43en')

This ensures:
- `makemigrations study_43en` includes AuditLog tables
- Tables are created in the 'logging' schema of each study database
- No duplicate code across studies

Security Features:
- HMAC-SHA256 checksum for tamper detection
- Immutable records (no update/delete allowed)
- IP address and session tracking
"""
from django.db import models
from django.core.exceptions import PermissionDenied
from django.utils import timezone


class AbstractAuditLog(models.Model):
    """
    Abstract base audit log entry
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
        abstract = True
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
    
    NOTE: ForeignKey to AuditLog is added by factory function
    """
    
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
        abstract = True
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


# =============================================================================
# FACTORY FUNCTION - Creates concrete models for each study
# =============================================================================

# Cache to store created models per study
_audit_model_cache = {}


def create_audit_models(app_label: str, index_prefix: str = None):
    """
    Factory function to create AuditLog and AuditLogDetail models for a study.
    
    Args:
        app_label: The study app label (e.g., 'study_43en', 'study_44en')
        index_prefix: Optional prefix for index names (default: first 3 chars of app_label)
    
    Returns:
        tuple: (AuditLog, AuditLogDetail) concrete model classes
    
    Usage:
        # In study_43en/models/__init__.py
        from backends.audit_logs.models.base import create_audit_models
        AuditLog, AuditLogDetail = create_audit_models('study_43en')
    """
    # Return cached models if already created
    if app_label in _audit_model_cache:
        return _audit_model_cache[app_label]
    
    # Default index prefix from app_label (e.g., 'study_43en' -> 's43')
    if index_prefix is None:
        # Extract number from app_label like 'study_43en' -> '43'
        import re
        match = re.search(r'(\d+)', app_label)
        index_prefix = f"s{match.group(1)}" if match else app_label[:3]
    
    # Store in local variables for closure
    _app_label = app_label
    _index_prefix = index_prefix
    
    # Create Meta class for AuditLog
    class AuditLogMeta:
        app_label = _app_label
        db_table = 'logging"."audit_log'
        db_table_comment = 'Audit log entries for tracking data changes'
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        default_permissions = ('add', 'view')
        indexes = [
            models.Index(fields=['-timestamp'], name=f'{_index_prefix}_audit_log_time_idx'),
            models.Index(fields=['patient_id', '-timestamp'], name=f'{_index_prefix}_audit_log_patient_idx'),
            models.Index(fields=['user_id', '-timestamp'], name=f'{_index_prefix}_audit_log_user_idx'),
            models.Index(fields=['SITEID', '-timestamp'], name=f'{_index_prefix}_audit_log_site_idx'),
            models.Index(fields=['model_name', 'action'], name=f'{_index_prefix}_audit_log_model_idx'),
        ]
    
    # Create AuditLog model using type()
    AuditLog = type('AuditLog', (AbstractAuditLog,), {'Meta': AuditLogMeta, '__module__': f'backends.studies.{_app_label}.models'})
    
    # Create Meta class for AuditLogDetail
    class AuditLogDetailMeta:
        app_label = _app_label
        db_table = 'logging"."audit_log_detail'
        db_table_comment = 'Audit log detail entries for field-level changes'
        ordering = ['field_name']
        verbose_name = 'Audit Log Detail'
        verbose_name_plural = 'Audit Log Details'
        default_permissions = ('add', 'view')
        indexes = [
            models.Index(fields=['audit_log', 'field_name'], name=f'{_index_prefix}_audit_detail_idx'),
        ]
    
    # Create AuditLogDetail model using type()
    AuditLogDetail = type('AuditLogDetail', (AbstractAuditLogDetail,), {
        'Meta': AuditLogDetailMeta,
        '__module__': f'backends.studies.{_app_label}.models',
        'audit_log': models.ForeignKey(
            AuditLog,
            on_delete=models.PROTECT,
            related_name='details'
        ),
    })
    
    # Cache the models
    _audit_model_cache[_app_label] = (AuditLog, AuditLogDetail)
    
    return AuditLog, AuditLogDetail


def get_audit_models(app_label: str):
    """
    Get cached audit models for a study.
    
    Returns None if models haven't been created yet.
    """
    return _audit_model_cache.get(app_label)
