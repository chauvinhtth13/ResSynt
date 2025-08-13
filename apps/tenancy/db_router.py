# apps/tenancy/db_router.py
# This defines the StudyDBRouter for routing database queries based on app_label and current study context.
# Assumptions:
# - Management apps (like 'tenancy' for metadata, auth, etc.) always use 'db_management'.
# - Other apps (study-specific data) use the current study's DB alias, retrieved from thread-local context.
# - Migrations: Allow migrations on 'db_management' for management apps; on study DBs for data apps.
# - Dynamic DB loading is handled in AppConfig or a separate loader.

from threading import local
from django.conf import settings

_thread_local = local()

def get_current_db():
    """Get the current study DB alias from thread-local storage."""
    return getattr(_thread_local, 'current_db', 'db_management')

def set_current_db(db_alias):
    """Set the current study DB alias in thread-local storage."""
    setattr(_thread_local, 'current_db', db_alias)

class StudyDBRouter:
    management_apps = [
        'auth', 'admin', 'contenttypes', 'sessions', 'messages', 'staticfiles', 'tenancy'
    ]  # Apps that use the main DB

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.management_apps:
            return 'db_management'
        return get_current_db()

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.management_apps:
            return 'db_management'
        return get_current_db()

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations if both objects are in management apps or both in study apps
        db1 = self.db_for_read(obj1.__class__)
        db2 = self.db_for_read(obj2.__class__)
        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'db_management':
            return app_label in self.management_apps
        elif db.startswith(settings.STUDY_DB_PREFIX):
            return app_label not in self.management_apps
        return False