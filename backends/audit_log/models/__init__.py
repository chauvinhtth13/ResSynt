# backends/audit_log/models/__init__.py
"""
🌐 BASE Audit Log Models - Shared across all studies
"""
from .audit_log import AuditLog, AuditLogDetail

__all__ = ['AuditLog', 'AuditLogDetail']
