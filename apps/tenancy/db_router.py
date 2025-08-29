# apps/tenancy/db_router.py - FIXED
import threading
from typing import Optional
from django.conf import settings
import logging

logger = logging.getLogger("apps.tenancy")
THREAD_LOCAL = threading.local()

def get_current_db() -> str:
    """Get current DB with fallback to default."""
    return getattr(THREAD_LOCAL, 'current_db', 'default')

def set_current_db(db_alias: str) -> None:
    """Set current DB with validation."""
    if db_alias and isinstance(db_alias, str):
        setattr(THREAD_LOCAL, 'current_db', db_alias)
    else:
        logger.warning(f"Invalid db_alias: {db_alias}, using default")
        setattr(THREAD_LOCAL, 'current_db', 'default')

class StudyDBRouter:
    # Apps that MUST stay in management DB
    management_apps = {
        'auth', 'admin', 'contenttypes', 'sessions', 
        'messages', 'staticfiles', 'tenancy', 'web', 'parler',
        'axes',  # ADD THIS - axes must be in management DB
        'axes_accessattempt',  # ADD THIS
        'axes_accesslog',  # ADD THIS
        'axes_accessfailurelog'  # ADD THIS
    }

    def db_for_read(self, model, **hints) -> str:
        try:
            if model._meta.app_label in self.management_apps:
                return 'default'
            return get_current_db()
        except Exception as e:
            logger.error(f"Router error: {e}")
            return 'default'

    def db_for_write(self, model, **hints) -> str:
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints) -> Optional[bool]:
        db1 = self.db_for_read(obj1.__class__)
        db2 = self.db_for_read(obj2.__class__)
        return db1 == db2 if db1 and db2 else None

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> bool:
        # CRITICAL: Allow axes migrations on default DB
        if app_label == 'axes':
            return db == 'default'
        
        if db == 'default':
            return app_label in self.management_apps
        if db.startswith(settings.STUDY_DB_PREFIX):
            return app_label not in self.management_apps
        return False