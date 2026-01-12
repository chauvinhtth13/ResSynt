# backends/audit_logs/__init__.py
"""
Audit Log System - Factory-based approach for multi-study databases

Provides:
- Factory function: create_audit_models() to create AuditLog/AuditLogDetail per study
- Abstract base models: AbstractAuditLog, AbstractAuditLogDetail
- Utils: decorators, helpers, validators, etc.

Usage in study models/__init__.py:
    from backends.audit_logs.models import create_audit_models
    AuditLog, AuditLogDetail = create_audit_models('study_43en')

Usage in views/decorators:
    from backends.studies.study_43en.models import AuditLog, AuditLogDetail
"""
default_app_config = 'backends.audit_logs.apps.AuditLogsConfig'

# Don't import models here - causes AppRegistryNotReady error
# Import from backends.audit_logs.models directly instead

__all__ = []
