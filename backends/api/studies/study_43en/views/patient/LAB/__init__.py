# backends/studies/study_43en/views/patient/LAB/__init__.py
"""
LAB Views Package

Exports all LAB-related views for URL configuration
- Microbiology Cultures with Semantic IDs (LAB_CULTURE_ID)
- Antibiotic Sensitivity Tests with WHONET codes (AST_ID)
"""

from .views_lab_micro import (
    microbiology_list,
    microbiology_create,
    microbiology_update,
    microbiology_get,
)

from .views_antibiotic_sensitivity import (
    antibiotic_list,
    antibiotic_create,
    antibiotic_update,
    antibiotic_get,
    antibiotic_statistics,
)

__all__ = [
    # Microbiology Culture Views
    'microbiology_list',
    'microbiology_create',
    'microbiology_update',
    'microbiology_get',
    
    # Antibiotic Sensitivity Views
    'antibiotic_list',
    'antibiotic_create',
    'antibiotic_update',
    'antibiotic_get',
    'antibiotic_statistics',
]
