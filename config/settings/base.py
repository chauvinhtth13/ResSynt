"""
Base Django settings - shared between all environments.

This file contains settings that are common to both development and production.
Environment-specific settings are in dev.py and prod.py.
"""
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

from config.utils import (
    load_study_apps,
    DatabaseConfig,
    build_fernet_keys,
    validate_salt_key,
)
from .security import *  # noqa: F401, F403
from .logging import LOGGING  # noqa: F401

# =============================================================================
# ENVIRONMENT & PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, None),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)

# =============================================================================
# CORE SETTINGS
# =============================================================================

SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError("SECRET_KEY must be at least 50 characters")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production")

AUTH_USER_MODEL = "tenancy.User"
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1

# =============================================================================
# APPLICATIONS
# =============================================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.usersessions",
    "axes",
    "csp",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "django_extensions"
]

LOCAL_APPS = [
    "backends.tenancy",
    "backends.audit_logs",
    "backends.api",
    "backends.studies",
]

STUDY_APPS, HAS_STUDY_ERRORS = load_study_apps()

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + STUDY_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "backends.tenancy.middleware.UnifiedTenancyMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
    "backends.tenancy.middleware.BlockSignupMiddleware",
    "csp.middleware.CSPMiddleware",
]

# =============================================================================
# DATABASE
# =============================================================================

STUDY_DB_PREFIX = env("STUDY_DB_PREFIX", default="db_study_")
STUDY_DB_SCHEMA = env("STUDY_DB_SCHEMA", default="data")
MANAGEMENT_DB_SCHEMA = env("MANAGEMENT_DB_SCHEMA", default="management")

DATABASES = {
    "default": DatabaseConfig.get_management_db(env),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

DatabaseConfig.validate_config(DATABASES["default"], "default")

# Load study databases
from backends.studies.study_loader import get_study_databases

study_databases = get_study_databases()
if study_databases:
    DATABASES.update(study_databases)

DATABASE_ROUTERS = ["backends.tenancy.db_router.TenantRouter"]

# =============================================================================
# CACHE & SESSION
# =============================================================================

# Use Redis if available, otherwise fall back to in-memory cache
REDIS_URL = env("REDIS_URL", default=None)

if REDIS_URL:  # Fixed: was "if not REDIS_URL is None"
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "resync",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,  # Graceful degradation if Redis unavailable
                "SOCKET_CONNECT_TIMEOUT": 2,  # Connection timeout (seconds)
                "SOCKET_TIMEOUT": 2,  # Read/Write timeout (seconds)
                "CONNECTION_POOL_CLASS_KWARGS": {
                    "max_connections": 20,
                    "timeout": 2,  # Pool timeout (seconds)
                },
            },
        }
    }
else:
    # Fallback for development without Redis - use in-memory cache for speed
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "resync-cache",
        }
    }

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = "resync"

SESSION_COOKIE_NAME = env("SESSION_COOKIE_NAME", default="resync_sessionid")
# Use database sessions (simpler, no cache dependency for critical auth)
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=28800)  # 8 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False

# =============================================================================
# AUTHENTICATION
# =============================================================================

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",  # MUST BE FIRST - intercepts all auth attempts
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Allauth
ACCOUNT_ADAPTER = "backends.api.base.account.adapter.CustomAccountAdapter"
ACCOUNT_ALLOW_REGISTRATION = False
SOCIALACCOUNT_ALLOW_REGISTRATION = False
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_BLACKLIST = ["admin", "administrator", "root", "system"]
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[ResSynt - Research Data Management Platform]"
ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_LOGOUT_ON_GET = False  # Require POST for logout (CSRF protection)
# Allauth rate limits (first layer of protection)
# login_failed: 5 attempts per minute per IP - shows allauth rate limit message
ACCOUNT_RATE_LIMITS = {
    "change_password": "5/m/user",
    "reset_password": "10/m/ip",
    "reset_password_email": "5/m/ip",
    "reset_password_from_key": "20/m/ip",
    "login_failed": "5/m/ip",  # 5 failed logins per minute triggers allauth rate limit
}

USERSESSIONS_TRACK_ACTIVITY = True

# Auth URLs
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"

# =============================================================================
# AXES (Brute-force protection)
# =============================================================================
# Flow: Wrong password → Allauth rate limit (5/min) → Axes block (7 total)

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 7
AXES_COOLOFF_TIME = None  # Manual unblock required
# Lock by username+IP combo (not separately) - prevents locking entire IP
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = False  # We handle reset manually per-username in signals
AXES_LOCK_OUT_AT_FAILURE = True
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

# Form field mapping (must match allauth LoginForm)
AXES_USERNAME_FORM_FIELD = "login"
AXES_PASSWORD_FORM_FIELD = "password"
AXES_SENSITIVE_PARAMETERS = ["password"]

# Custom lockout response
AXES_LOCKOUT_CALLABLE = "backends.api.base.account.lockout.lockout_response"
AXES_LOCKOUT_URL = "/accounts/login/"

# IP detection (for reverse proxy)
AXES_IPWARE_PROXY_COUNT = 1
AXES_IPWARE_META_PRECEDENCE_ORDER = [
    "HTTP_X_FORWARDED_FOR",
    "X_FORWARDED_FOR", 
    "REMOTE_ADDR",
]

# Logging (disable in production for performance)
AXES_VERBOSE = False
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# IP Whitelist - these IPs are never locked out (useful for admin access)
# Format: comma-separated IPs in env, e.g., "192.168.1.1,10.0.0.1"
AXES_NEVER_LOCKOUT_WHITELIST = env.list("AXES_IP_WHITELIST", default=[])

# Whitelist GET requests (only lock out on failed POSTs)
AXES_NEVER_LOCKOUT_GET = True

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontends" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                "django.template.context_processors.media",
                "django.template.context_processors.tz",
                "backends.studies.study_loader.dynamic_study_context",
            ],
        },
    },
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

USE_I18N = True
USE_TZ = True
USE_L10N = False  # Use custom date/time formats instead of locale-specific formats
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"

LANGUAGES = [
    ("vi", _("Tiếng Việt")),
    ("en", _("English")),
]

LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60
LANGUAGE_COOKIE_SECURE = not DEBUG
LANGUAGE_COOKIE_HTTPONLY = False
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGE_SESSION_KEY = "_language"

LOCALE_PATHS = [BASE_DIR / "locale"]

# Date/time formats (Vietnamese)
DATE_FORMAT = "d/m/Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = "d/m/Y H:i:s"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
FIRST_DAY_OF_WEEK = 1

DATE_INPUT_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"]
TIME_INPUT_FORMATS = ["%H:%M:%S", "%H:%M"]
DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]

# Number formats (Vietnamese)
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
NUMBER_GROUPING = 3

# Parler
PARLER_DEFAULT_LANGUAGE_CODE = "vi"
PARLER_LANGUAGES = {
    None: ({"code": "vi"}, {"code": "en"}),
    "default": {"fallbacks": ["vi", "en"], "hide_untranslated": False},
}

# =============================================================================
# STATIC & MEDIA
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontends" / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# =============================================================================
# EMAIL
# =============================================================================
# EMAIL_BACKEND is set in dev.py (console) and prod.py (smtp)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@resync.local")
SERVER_EMAIL = env("SERVER_EMAIL", default="server@resync.local")

# =============================================================================
# CELERY
# =============================================================================
# Dev: CELERY_TASK_ALWAYS_EAGER=True (synchronous, no broker needed)
# Prod: CELERY_TASK_ALWAYS_EAGER=False (async with Redis)

CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=True)
CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# =============================================================================
# RATE LIMITING
# =============================================================================

RATELIMIT_ENABLE = env.bool("RATELIMIT_ENABLE", default=True)
RATELIMIT_USE_CACHE = "default"

# API Rate Limiting Configuration (used by UnifiedTenancyMiddleware)
# Requests per minute by user type
API_RATE_LIMITS = {
    "authenticated": env.int("API_RATE_LIMIT_AUTH", default=60),     # 60/min for logged in users
    "anonymous": env.int("API_RATE_LIMIT_ANON", default=10),         # 10/min for anonymous
    "api_key": env.int("API_RATE_LIMIT_API_KEY", default=120),       # 120/min for API key auth
    "admin": env.int("API_RATE_LIMIT_ADMIN", default=300),           # 300/min for admins
}

# Rate limit window in seconds
API_RATE_LIMIT_WINDOW = env.int("API_RATE_LIMIT_WINDOW", default=60)

# =============================================================================
# ENCRYPTION & SECURITY KEYS
# =============================================================================

# Fernet encryption keys (supports key rotation)
# Primary key is used for encryption, old keys are used for decryption during rotation
# Validation is handled by build_fernet_keys() in config/utils.py
FERNET_KEYS = build_fernet_keys(
    primary_key=env("FIELD_ENCRYPTION_KEY"),
    old_key=env("FIELD_ENCRYPTION_KEY_OLD", default=None),
)

# Salt key for encrypted_fields (required)
# Validation is handled by validate_salt_key() in config/utils.py
SALT_KEY = validate_salt_key(env("SALT_KEY", default=None))

# Backup encryption (required in production, validated in prod.py)
BACKUP_ENCRYPTION_PASSWORD = env("BACKUP_ENCRYPTION_PASSWORD", default=None)

# Password reset link expiration
PASSWORD_RESET_TIMEOUT = 60 * 15  # 15 minutes

# =============================================================================
# ORGANIZATION & ADMIN
# =============================================================================

ORGANIZATION_NAME = env("ORGANIZATION_NAME", default="ResSynt Research Platform")
PLATFORM_VERSION = env("PLATFORM_VERSION", default="1.0.0")
SERVER_NAME = env("SERVER_NAME", default="ReSynt Production")
BACKUP_RETENTION_DAYS = env.int("BACKUP_RETENTION_DAYS", default=90)

ADMINS = [
    ("Security Team", env("ADMIN_EMAIL", default="admin@resynt.local")),
]

# =============================================================================
# HEALTH CHECK
# =============================================================================

HEALTH_CHECK = {
    "DISK_USAGE_MAX": 90,  # Alert if disk usage > 90%
    "MEMORY_MIN": 100,     # Alert if memory < 100MB
}

# django-health-check configuration
HEALTH_CHECK_CONTRIB_INSTALLED_APPS = True

# Custom health check settings
HEALTH_CHECK_SETTINGS = {
    # Database check
    "db_timeout": 5,  # seconds
    
    # Cache check
    "cache_key": "health_check_test",
    "cache_timeout": 10,  # seconds
    
    # Disk check
    "disk_path": "/",  # Path to check disk usage
    "disk_usage_max": 90,  # Max percentage
    
    # Memory check
    "memory_min_mb": 100,  # Minimum free memory in MB
    
    # Response time thresholds (ms)
    "response_time_warning": 500,
    "response_time_critical": 2000,
}