from django.apps import AppConfig


class Study43EnConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'study_43en'
    verbose_name = '43EN Study'


class Study43enConfig(AppConfig):
    name = 'study_43en'

    def ready(self):
        import study_43en.signals