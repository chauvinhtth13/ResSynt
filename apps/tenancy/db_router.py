# apps/tenancy/db_router.py
from contextvars import ContextVar

_current_db = ContextVar("current_db", default="db_management")

def set_current_db(alias: str):
    _current_db.set(alias)

def get_current_db():
    return _current_db.get()

class StudyDBRouter:
    """Route: auth/metadata -> db_management; còn lại -> DB theo study (đã set trong middleware)."""
    management_apps = {"auth", "admin", "contenttypes", "sessions", "tenancy"}

    def db_for_read(self, model, **hints):
        return "db_management" if model._meta.app_label in self.management_apps else get_current_db()

    def db_for_write(self, model, **hints):
        return "db_management" if model._meta.app_label in self.management_apps else get_current_db()

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # metadata & auth chỉ migrate ở db_management (thực tế managed=False nên không migrate)
        if app_label in self.management_apps:
            return db == "db_management"
        # dữ liệu nghiên cứu migrate ở DB study khi bạn chạy migrate --database=<alias>
        return db != "db_management"
