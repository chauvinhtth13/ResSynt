# backends/audit_log/apps.py
"""
Django App Configuration for Base Audit Log System
"""
from django.apps import AppConfig


class AuditLogConfig(AppConfig):
    """
    Configuration for the base audit log application.
    
    This app provides shared audit log functionality for all studies.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.audit_log'
    label = 'audit_log'
    verbose_name = 'Audit Log System'
