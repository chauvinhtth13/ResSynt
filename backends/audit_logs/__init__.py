# backends/audit_logs/__init__.py
"""
BASE Audit Log System - Shared across all studies

Provides:
- Models: AuditLog, AuditLogDetail
- Utils: decorators, helpers, validators, etc.

Usage in studies:
    from backends.audit_logs.models import AuditLog, AuditLogDetail
    from backends.audit_logs.utils import audit_log, ChangeDetector, ReasonValidator
"""
default_app_config = 'backends.audit_logs.apps.AuditLogsConfig'

# Don't import models here - causes AppRegistryNotReady error
# Import from backends.audit_logs.models directly instead

__all__ = []
