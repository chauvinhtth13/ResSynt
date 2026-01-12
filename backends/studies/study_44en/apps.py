from django.apps import AppConfig

class Study44ENConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.studies.study_44en'
    label = 'study_44en'  # CRITICAL: This label is used for migrations and database routing
    verbose_name = "Study 44EN"
    
    def ready(self):
        """App initialization - Import signals to register them"""
        # Import signals to ensure they are registered
        from backends.api.studies.study_44en.services import signals
