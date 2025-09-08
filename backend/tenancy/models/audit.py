# backend/tenancy/models/audit.py - FIXED VERSION
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """Audit trail for all data changes"""
    
    class Action(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        SOFT_DELETE = 'SOFT_DELETE', _('Soft Delete')
        RESTORE = 'RESTORE', _('Restore')
        EXPORT = 'EXPORT', _('Export')
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        LOGIN_FAILED = 'LOGIN_FAILED', _('Login Failed')
        PERMISSION_DENIED = 'PERMISSION_DENIED', _('Permission Denied')
    
    # Study and Site context
    study = models.ForeignKey(
        'Study',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_("Study")
    )
    
    site_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Site ID")
    )
    
    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Content Type")
    )
    
    object_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Object ID")
    )
    
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action details
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        db_index=True,
        verbose_name=_("Action")
    )
    
    table_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Table Name")
    )
    
    record_display = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Record Display"),
        help_text=_("Human-readable representation of the record")
    )
    
    # Change tracking
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Changes"),
        help_text=_("JSON object with old and new values")
    )
    
    # User and request information
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='audit_logs',
        verbose_name=_("Performed By")
    )
    
    performed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Performed At")
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address")
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent")
    )
    
    session_key = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Session Key")
    )
    
    # Additional context
    request_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name=_("Request ID"),
        help_text=_("Unique identifier for the request")
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    class Meta:
        db_table = 'audit_logs'  # FIXED: Added management schema
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['study', 'performed_at'], 
                        name='idx_audit_study_time'),
            models.Index(fields=['performed_by', 'performed_at'], 
                        name='idx_audit_user_time'),
            models.Index(fields=['action', 'performed_at'], 
                        name='idx_audit_action_time'),
            models.Index(fields=['table_name', 'object_id'], 
                        name='idx_audit_table_object'),
            models.Index(fields=['request_id'], 
                        name='idx_audit_request'),
        ]

    def __str__(self):
        return f"{self.action} - {self.table_name} - {self.performed_by} - {self.performed_at}"
    
    @classmethod
    def log_action(cls, user, action, obj=None, changes=None, request=None, **kwargs):
        """Helper method to create audit log entry"""
        log_entry = {
            'performed_by': user,
            'action': action,
        }
        
        # Add object information if provided
        if obj:
            log_entry.update({
                'content_type': ContentType.objects.get_for_model(obj.__class__),
                'object_id': str(obj.pk),
                'table_name': obj._meta.db_table,
                'record_display': str(obj),
            })
        
        # Add changes if provided
        if changes:
            log_entry['changes'] = changes
        
        # Add request information if provided
        if request:
            log_entry.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_key': request.session.session_key if hasattr(request, 'session') else '',
            })
        
        # Add any additional kwargs
        log_entry.update(kwargs)
        
        return cls.objects.create(**log_entry)
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip