# backends/studies/study_43en/views/discharge/__init__.py
"""
Discharge Views Package

Exports all discharge-related views for URL configuration
"""

from .views_disch import (
    discharge_create,
    discharge_update,
    discharge_view,
)

__all__ = [
    'discharge_create',
    'discharge_update',
    'discharge_view',
]
