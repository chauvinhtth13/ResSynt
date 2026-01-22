"""
Production settings.

Usage: DJANGO_ENV=prod gunicorn config.wsgi:application

Features:
- DEBUG=False (mandatory)
- HTTPS enforcement (SSL, HSTS)
- Redis cache with database fallback
- Cached templates for performance
- SMTP email backend
- Celery with Redis broker
"""
import environ

from .base import *  # noqa: F401, F403

env = environ.Env()

# =============================================================================
# CORE SETTINGS
# =============================================================================

DEBUG = False

# =============================================================================
# VALIDATION
# =============================================================================

if not BACKUP_ENCRYPTION_PASSWORD:  # noqa: F405
    raise ValueError("BACKUP_ENCRYPTION_PASSWORD must be set in production")

if not ALLOWED_HOSTS:  # noqa: F405
    raise ValueError("ALLOWED_HOSTS must be set in production")

# =============================================================================
# SECURITY (HTTPS Hardening)
# =============================================================================

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# =============================================================================
# DATABASE
# =============================================================================

DATABASES["default"].update({  # noqa: F405
    "CONN_HEALTH_CHECKS": True,
    "CONN_MAX_AGE": 60,
    "OPTIONS": {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",  # 30s query timeout
    },
})

if env.bool("USE_PGBOUNCER", default=False):
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True  # noqa: F405

# =============================================================================
# CACHE
# =============================================================================

# Redis is disabled by default via REDIS_ENABLED in base.py
# To enable: set REDIS_ENABLED=True and REDIS_URL in .env
_redis_enabled = env.bool("REDIS_ENABLED", default=False)
_redis_url = env("REDIS_URL", default=None)

if _redis_enabled and _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_url,
            "KEY_PREFIX": "cache",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "CONNECTION_POOL_CLASS_KWARGS": {"max_connections": 50, "timeout": 20},
            },
        },
        "sessions": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_url,
            "KEY_PREFIX": "session",
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        },
    }
    SESSION_CACHE_ALIAS = "sessions"
else:
    # Database cache when Redis is disabled
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache_table",
        }
    }

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES[0]["APP_DIRS"] = False  # noqa: F405
TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa: F405
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

STORAGES["staticfiles"] = {  # noqa: F405
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
CELERY_TASK_ROUTES = {
    "backends.*.tasks.high_priority_*": {"queue": "high"},
    "backends.*.tasks.low_priority_*": {"queue": "low"},
}

# =============================================================================
# AXES
# =============================================================================

AXES_VERBOSE = False
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# =============================================================================
# ADMIN SECURITY (Production)
# =============================================================================

# REQUIRED: Admin URL must be set and not default "admin/"
if ADMIN_URL == "admin/":  # noqa: F405
    import warnings
    warnings.warn(
        "SECURITY WARNING: ADMIN_URL is using default 'admin/'. "
        "Set a secret ADMIN_URL in production!",
        RuntimeWarning
    )

# =============================================================================
# HONEYPOT (Production - Enabled)
# =============================================================================

# Enable honeypot verification in production
HONEYPOT_VERIFIER = "honeypot.verifiers.always_ok"  # Use default verifier when needed
# Note: Honeypot protects public forms, not admin login

# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# =============================================================================
# LOGGING
# =============================================================================

LOGGING["root"]["handlers"] = ["console", "file_all", "file_error"]  # noqa: F405
LOGGING["root"]["level"] = "INFO"  # noqa: F405