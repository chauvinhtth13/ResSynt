# backends/studies/study_43en/models/audit_log.py
"""
Audit Log Model - Track user activities and data changes
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from backends.studies.study_43en.study_site_manage import SiteFilteredManage
from backends.studies.study_43en.utils.audit_log_utils import safe_json_loads


class AuditLog(models.Model):
    """
    Audit log for tracking user activities
    Records all CREATE, UPDATE, DELETE, VIEW actions
    """
    
    # Choices definition (keep original format)
    ACTION_CHOICES = [
        ('CREATE', _('Create')),
        ('UPDATE', _('Update')),
        ('DELETE', _('Delete')),
        ('VIEW', _('View')),
    ]
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # User information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        verbose_name=_('User')
    )
    username = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name=_('Username')
    )
    
    # Action details
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_('Timestamp')
    )
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name=_('Action')
    )
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_('Model Name')
    )
    patient_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_('Patient ID')
    )
    SITEID = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Site ID')
    )
    
    # Data changes
    old_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Old Data')
    )
    new_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('New Data')
    )
    
    # Additional info
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Change Reason')
    )
    reasons_json = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Field-wise Change Reasons')
    )
    
    class Meta:
        db_table = 'audit_log'
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'model_name'], name='idx_audit_time_model'),
            models.Index(fields=['patient_id', 'action'], name='idx_audit_patient_action'),
            models.Index(fields=['SITEID', '-timestamp'], name='idx_audit_site_time'),
        ]
    
    def __str__(self):
        username = self.username or (self.user.username if self.user else "unknown")
        action_display = dict(self.ACTION_CHOICES).get(self.action, self.action)
        return f"{username} - {action_display} {self.model_name} #{self.patient_id}"
    
    def save(self, *args, **kwargs):
        """Auto-populate username from user"""
        if self.user and not self.username:
            self.username = self.user.username
        super().save(*args, **kwargs)
    
    def get_old_data_dict(self):
        """Get old data as flattened dictionary"""
        if not self.old_data:
            return {}
        if isinstance(self.old_data, dict):
            return self.old_data
        return flatten_formset_data(safe_json_loads(self.old_data, {}))

    def get_new_data_dict(self):
        """Get new data as flattened dictionary"""
        if not self.new_data:
            return {}
        if isinstance(self.new_data, dict):
            return self.new_data
        return flatten_formset_data(safe_json_loads(self.new_data, {}))


def flatten_formset_data(data):
    """
    Flatten formset data structure to simple key-value pairs
    
    Args:
        data: Dictionary potentially containing nested formset arrays
        
    Returns:
        Flattened dictionary with keys like 'antibiotic_0_field'
    """
    if not isinstance(data, dict):
        return {}
            
    result = {}
    
    # Handle main + nested formsets structure
    if 'main' in data:
        # Add main fields
        for k, v in data.get('main', {}).items():
            result[k] = v
        
        # Flatten antibiotic formset
        antibiotics = data.get('antibiotic', [])
        for idx, item in enumerate(antibiotics):
            if item:
                for field, value in item.items():
                    result[f"antibiotic_{idx}_{field}"] = value
        
        # Flatten rehospitalization formset
        rehospitalizations = data.get('rehospitalization', [])
        for idx, item in enumerate(rehospitalizations):
            if item:
                for field, value in item.items():
                    result[f"rehospitalization_{idx}_{field}"] = value
    else:
        # Handle direct structure
        for k, v in data.items():
            if isinstance(v, list):
                for idx, row in enumerate(v):
                    if row:
                        for field, value in row.items():
                            result[f"{k}_{idx}_{field}"] = value
            else:
                result[k] = v
                
    return result