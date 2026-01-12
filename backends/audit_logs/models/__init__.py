# backends/audit_logs/models/__init__.py
"""
Audit Log Models - Factory-based approach

This module provides a factory function to create AuditLog and AuditLogDetail
models for each study. This ensures:
- `makemigrations study_XXen` includes AuditLog tables
- Tables are created in the 'log' schema of each study database
- No duplicate code across studies

Usage in study app (e.g., study_43en/models/__init__.py):
    from backends.audit_logs.models import create_audit_models
    
    # Create concrete AuditLog and AuditLogDetail for this study
    AuditLog, AuditLogDetail = create_audit_models('study_43en')
    
    # Export them
    __all__ = ['AuditLog', 'AuditLogDetail', ...]

For runtime usage (views, decorators, etc.):
    from backends.audit_logs.models import get_audit_models
    
    AuditLog, AuditLogDetail = get_audit_models('study_43en')
    # or import directly from study
    from backends.studies.study_43en.models import AuditLog, AuditLogDetail
"""

from .base import (
    AbstractAuditLog,
    AbstractAuditLogDetail,
    create_audit_models,
    get_audit_models,
)

__all__ = [
    # Abstract base models
    'AbstractAuditLog',
    'AbstractAuditLogDetail',
    # Factory function
    'create_audit_models',
    'get_audit_models',
]