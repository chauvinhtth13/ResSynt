# backends/studies/study_44en/study_site_manage.py

"""
Study 44EN Site Management Configuration

This module provides study-specific configuration and exports
the site filtering utilities from base_models for convenience.
"""

STUDY_CODE = '44EN'
STUDY_NAME = 'Study 44EN'
DATABASE_NAME = 'db_study_44en'
SCHEMA_NAME = 'data'

# Re-export site filtering components for convenience
from backends.studies.study_44en.models.base_models import (
    SiteFilteredManager,
    SiteFilteredQuerySet,
    DB_ALIAS,
    _validate_hhid,
    _get_cached_model_fields,
)
