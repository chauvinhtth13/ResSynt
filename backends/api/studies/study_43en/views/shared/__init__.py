# backends/api/studies/study_43en/views/shared/__init__.py
"""
Shared utilities for all views in study_43en.

This module contains common functions used across patient and contact views,
reducing code duplication and ensuring consistency.
"""

from .audit import set_audit_metadata
from .forms import make_form_readonly, make_formset_readonly
from .queries import (
    get_case_with_enrollment,
    get_patient_case_chain,
    get_contact_case_chain,
)

__all__ = [
    'set_audit_metadata',
    'make_form_readonly',
    'make_formset_readonly',
    'get_case_with_enrollment',
    'get_patient_case_chain',
    'get_contact_case_chain',
]
