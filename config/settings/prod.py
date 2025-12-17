"""
Production settings.

Usage: DJANGO_ENV=prod gunicorn config.wsgi:application
"""
import environ
from .base import *

env = environ.Env()

DEBUG = False

# =============================================================================
# SECURITY HARDENING
# =============================================================================

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# =============================================================================
# DATABASE OPTIMIZATION
# =============================================================================

DATABASES["default"].update({
    "CONN_HEALTH_CHECKS": True,
    "CONN_MAX_AGE": 60,
    "OPTIONS": {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",  # 30s query timeout
    },
})

# PgBouncer support
if env.bool("USE_PGBOUNCER", default=False):
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# =============================================================================
# CACHE (Redis)
# =============================================================================

redis_url = env("REDIS_URL", default=None)

if redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "KEY_PREFIX": "cache",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "CONNECTION_POOL_CLASS_KWARGS": {
                    "max_connections": 50,
                    "timeout": 20,
                },
            },
        },
        "sessions": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "KEY_PREFIX": "session",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        },
    }
    SESSION_CACHE_ALIAS = "sessions"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache_table",
        }
    }

# =============================================================================
# TEMPLATES (cached)
# =============================================================================

TEMPLATES[0]["APP_DIRS"] = False
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ),
]

# =============================================================================
# STATIC FILES
# =============================================================================

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}

# =============================================================================
# CELERY
# =============================================================================

CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_POOL_LIMIT = 10
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100

# Task routing
CELERY_TASK_ROUTES = {
    "backends.*.tasks.high_priority_*": {"queue": "high"},
    "backends.*.tasks.low_priority_*": {"queue": "low"},
}

# =============================================================================
# AXES (stricter in production)
# =============================================================================

AXES_VERBOSE = False
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# =============================================================================
# EMAIL (SMTP in production)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# =============================================================================
# LOGGING
# =============================================================================

# Remove console_dev, keep only error-level console output
LOGGING["root"]["handlers"] = ["console", "file_all", "file_error"]
LOGGING["root"]["level"] = "INFO"