# backends/audit_logs/apps.py
"""
Django App Configuration for Base Audit Log System

LIBRARY MODE: This app provides shared audit log functionality.
Models are marked as managed=False - no migrations will be created.

Study apps should:
1. Inherit from AuditLog/AuditLogDetail in models/base.py
2. Create their own concrete models with proper app_label
3. Run makemigrations for their own app

Configuration in settings.py:
    AUDIT_LOG_MODEL = 'study_43en.AuditLog'
    AUDIT_LOG_DETAIL_MODEL = 'study_43en.AuditLogDetail'
"""
from django.apps import AppConfig


class AuditLogConfig(AppConfig):
    """
    Configuration for the base audit log application.
    
    This app provides shared audit log functionality for all studies.
    No migrations are created for this app (library mode).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.audit_logs'
    label = 'audit_logs'
    verbose_name = 'Audit Log System (Library)'
