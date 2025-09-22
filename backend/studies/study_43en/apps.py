from django.apps import AppConfig


class Study43EnConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.studies.study_43en'
    label = 'study_43en'  # CRITICAL: This label is used for migrations and database routing
    verbose_name = "Study 43EN - Clinical Trial Data"
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signal handlers if needed
        try:
            from . import signals
        except ImportError:
            pass