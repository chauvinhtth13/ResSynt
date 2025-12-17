"""
Celery Configuration for ResSync Platform
"""
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('ressync')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# ==========================================
# SCHEDULED TASKS (Periodic Tasks)
# ==========================================
app.conf.beat_schedule = {
    # Daily backup at 2:00 AM
    'daily-database-backup': {
        'task': 'backends.tenancy.tasks.scheduled_backup_all_databases',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM every day
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
    
    # Weekly cleanup old backups (Sunday 3:00 AM)
    'weekly-backup-cleanup': {
        'task': 'backends.tenancy.tasks.cleanup_old_backups',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3:00 AM
        'options': {
            'expires': 7200,
        }
    },
    
    # Daily session cleanup (4:00 AM)
    'daily-session-cleanup': {
        'task': 'backends.tenancy.tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=4, minute=0),
        'options': {
            'expires': 3600,
        }
    },
}

# ==========================================
# CELERY CONFIGURATION
# ==========================================
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    
    # Retry settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')
