# backends/studies/apps.py - FINAL VERSION
"""
Base Studies App Configuration
NO DATABASE QUERIES - to avoid RuntimeWarning
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class StudiesConfig(AppConfig):
    """
    Base studies app configuration
    
    This is the parent app for all study-specific apps
    NO DATABASE QUERIES in ready() to avoid warnings
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.studies'
    verbose_name = "Studies"
    
    def ready(self):
        pass