# backends/audit_log/models/__init__.py
"""
BASE Audit Log Models - Shared across all studies
"""
# backends/audit_logs/models/__init__.py
"""
Audit Log Models

Provides both:
1. Abstract base models (for inheritance in study apps)
2. Concrete models (for direct use if needed)

RECOMMENDED: Use abstract models for study-specific databases
    from backends.audit_logs.models.base import AbstractAuditLog, AbstractAuditLogDetail

ALTERNATIVE: Use concrete models (requires audit_logs in INSTALLED_APPS with migrations)
    from backends.audit_logs.models import AuditLogs, AuditLogsDetail
"""

# Abstract base models (NO migrations needed)
from .base import AbstractAuditLog, AbstractAuditLogDetail

# Concrete models (migrations needed if used directly)
from .audit_logs import AuditLogs, AuditLogsDetail

__all__ = [
    # Abstract (recommended)
    'AbstractAuditLog',
    'AbstractAuditLogDetail',
    # Concrete
    'AuditLogs',
    'AuditLogsDetail',
]

__all__ = ['AuditLogs', 'AuditLogsDetail']