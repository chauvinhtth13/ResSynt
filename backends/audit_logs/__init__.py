# backends/audit_logs/__init__.py
"""
BASE Audit Log System - Shared across all studies

Provides:
- Models: AuditLog, AuditLogDetail
- Utils: decorators, helpers, validators, etc.

Usage in studies:
    from backends.audit_log.models import AuditLog, AuditLogDetail
    from backends.audit_log.utils import audit_log, ChangeDetector, ReasonValidator
"""
default_app_config = 'backends.audit_log.apps.AuditLogsConfig'

# Don't import models here - causes AppRegistryNotReady error
# Import from backends.audit_log.models directly instead

__all__ = []
