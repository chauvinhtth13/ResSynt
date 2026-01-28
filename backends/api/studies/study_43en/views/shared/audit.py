# backends/api/studies/study_43en/views/shared/audit.py
"""
Audit utilities shared across all views.
"""
import logging

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """
    Set audit fields on model instance.
    
    Args:
        instance: Model instance with audit fields
        user: Django User object
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username
