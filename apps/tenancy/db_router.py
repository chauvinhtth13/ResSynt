import threading
from django.conf import settings

THREAD_LOCAL = threading.local()

def get_current_db():
    """Get the current study DB alias from thread-local storage."""
    return getattr(THREAD_LOCAL, 'current_db', 'default')

def set_current_db(db_alias: str) -> None:
    """Set the current study DB alias in thread-local storage."""
    setattr(THREAD_LOCAL, 'current_db', db_alias)

class StudyDBRouter:
    # Keep all management/metadata apps on the default DB.
    management_apps = [
        'auth', 'admin', 'contenttypes', 'sessions', 'messages', 'staticfiles',
        'tenancy', 'web', 'parler'  # ensure parler models live in management DB
    ]

    def db_for_read(self, model, **hints):
        return 'default' if model._meta.app_label in self.management_apps else get_current_db()

    def db_for_write(self, model, **hints):
        return 'default' if model._meta.app_label in self.management_apps else get_current_db()

    def allow_relation(self, obj1, obj2, **hints):
        db1 = self.db_for_read(obj1.__class__)
        db2 = self.db_for_read(obj2.__class__)
        return db1 == db2 if db1 and db2 else None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'default':
            return app_label in self.management_apps
        if db.startswith(settings.STUDY_DB_PREFIX):
            return app_label not in self.management_apps
        return False
