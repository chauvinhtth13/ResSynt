from django.apps import AppConfig

class Study43ENConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.studies.study_43en'
    label = 'study_43en'  # CRITICAL: This label is used for migrations and database routing
    verbose_name = "Study 43EN"
    
    def ready(self):
        """App initialization - Import signals to register them"""
        # Import signals to ensure they are registered
        from backends.studies.study_43en.services import signals