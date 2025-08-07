# config/db_router.py

from django.conf import settings
from django.apps import apps

def get_study_db_config(study_code):
    """
    Truy vấn thông tin DB nghiên cứu từ apps.tenancy.models.Study.
    """
    Study = apps.get_model('tenancy', 'Study')
    study = Study.objects.get(study_code=study_code)
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': getattr(study, 'db_name', None),
        'USER': getattr(study, 'db_user', None),
        'PASSWORD': getattr(study, 'db_password', None),
        'HOST': getattr(study, 'db_host', None),
        'PORT': getattr(study, 'db_port', None),
    }


class StudyDBRouter:
    """
    Router tự động định tuyến các models theo app_label.
    - apps.tenancy và apps hệ thống -> db_management (default)
    - app nghiên cứu (label bắt đầu bằng 'study_') -> DB vật lý nghiên cứu (dynamic)
    """

    system_apps = {
        'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles',
        'tenancy'
    }

    def db_for_read(self, model, **hints):
        app_label = model._meta.app_label
        # App hệ thống, tenancy -> db_management
        if app_label in self.system_apps:
            return 'default'
        # App nghiên cứu (bắt đầu bằng study_)
        if app_label.startswith('study_'):
            # Lấy study_code từ hints hoặc app_label
            study_code = hints.get('study_code') or app_label
            db_name = self.ensure_study_db_connected(study_code)
            return db_name
        return None

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        db_obj1 = self.db_for_read(obj1._meta.model)
        db_obj2 = self.db_for_read(obj2._meta.model)
        if db_obj1 and db_obj2:
            return db_obj1 == db_obj2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # App hệ thống migrate vào db_management
        if app_label in self.system_apps:
            return db == 'default'
        # App nghiên cứu migrate vào đúng DB vật lý
        if app_label.startswith('study_'):
            # db (tên DB vật lý) sẽ là 'db_study_43en'
            return db == f"db_{app_label}"
        return None

    def ensure_study_db_connected(self, study_code):
        """
        Đảm bảo config DB nghiên cứu đã có trong settings.DATABASES,
        key là db_name, value là config DB.
        """
        # Lấy config DB và tên db_name (vd: 'db_study_43en') từ bảng Study
        db_config, db_name = get_study_db_config(study_code)
        if db_name not in settings.DATABASES:
            settings.DATABASES[db_name] = db_config
        return db_name
