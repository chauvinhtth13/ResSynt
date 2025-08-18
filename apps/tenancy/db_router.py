import threading
from django.conf import settings

THREAD_LOCAL = threading.local()

def get_current_db():
    """Get the current study DB alias from thread-local storage."""
    return getattr(THREAD_LOCAL, 'current_db', 'default')

def set_current_db(db_alias):
    """Set the current study DB alias in thread-local storage."""
    setattr(THREAD_LOCAL, 'current_db', db_alias)

class StudyDBRouter:
    management_apps = [
        'auth', 'admin', 'contenttypes', 'sessions', 'messages', 'staticfiles', 'tenancy'
    ]  # Apps that use the main DB (including 'tenancy' for metadata models like Study, Role, etc.)

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.management_apps:
            return 'default'
        return get_current_db()

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.management_apps:
            return 'default'
        return get_current_db()

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations if both objects are in management apps or both in study apps
        db1 = self.db_for_read(obj1.__class__)
        db2 = self.db_for_read(obj2.__class__)
        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'default':
            return app_label in self.management_apps
        elif db.startswith(settings.STUDY_DB_PREFIX):
            return app_label not in self.management_apps
        return False