"""
Clinical Views Package

Exports all clinical-related views
"""
from .views_clinical_case import clinical_case_create,clinical_case_update
from .views_readonly import clinical_case_view

__all__ = [
    'clinical_case_create',
    'clinical_case_update',
    'clinical_case_view',
]