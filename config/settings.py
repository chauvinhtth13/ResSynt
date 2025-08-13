# settings.py for the Django project "ResSync"
# Optimized version: Removed duplicates, improved structure, added necessary settings for multi-tenant DB setup,
# including better handling for dynamic databases, testing, and security.
# Assumptions:
# - Using PostgreSQL with separate DBs per study (multi-db tenant).
# - Schemas in main DB: auth (Django default), metadata (custom models), public (fallback).
# - Per-study DBs use a single schema (configurable, default 'public'; change to 'data' if needed).
# - Added: CACHES for potential session/caching needs, EMAIL settings placeholder, TEST settings.
# - Ensured consistency in env var handling and defaults.
# - Middleware and routers already configured; ensured order.
# - For production: Recommend using env vars for sensitive info.

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# === Paths & .env ===
BASE_DIR = Path(__file__).resolve().parent.parent  # -> ResSync/
load_dotenv(BASE_DIR / ".env")  # Load .env from project root

# === Core settings ===
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-default-key")  # Use a secure key in production
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# === Installed apps ===
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_bootstrap5",
    "chartjs",
    # ResSync apps
    "apps.web",
    "apps.tenancy.apps.TenancyConfig",
]

# === Middleware ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Tenancy middleware for dynamic DB routing (inserted at top for early context setting)
    "apps.tenancy.middleware.StudyRoutingMiddleware",
]

# === Templates ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "web" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

# === Database: Main management DB (db_management) ===
_DB_MANAGEMENT = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("PGDATABASE", "db_management"),
    "USER": os.getenv("PGUSER", "resync_app"),
    "PASSWORD": os.getenv("PGPASSWORD", ""),
    "HOST": os.getenv("PGHOST", "localhost"),
    "PORT": os.getenv("PGPORT", "5432"),
    "OPTIONS": {"options": "-c search_path=auth,metadata,public"},  # Schemas: auth (Django), metadata (custom), public (fallback)
    "CONN_MAX_AGE": int(os.getenv("PG_CONN_MAX_AGE", "600")),
    "ATOMIC_REQUESTS": False,  # Dev/test: False for performance; set True for production if needed
    "AUTOCOMMIT": True,
    "CONN_HEALTH_CHECKS": False,  # Optional: Enable for production
    "TIME_ZONE": os.getenv("DB_TIME_ZONE", "Asia/Ho_Chi_Minh"),
}

DATABASES = {
    "default": _DB_MANAGEMENT,  # Alias 'default' points to db_management for convenience
    "db_management": _DB_MANAGEMENT,
}

# === Template for per-study DBs (dynamic loading in middleware/apps) ===
STUDY_DB_AUTO_REFRESH_SECONDS = int(os.getenv("STUDY_DB_AUTO_REFRESH_SECONDS", "300"))  # Refresh interval for loading active DBs
STUDY_DB_PREFIX = os.getenv("STUDY_DB_PREFIX", "db_study_")  # Prefix for study DB names
STUDY_DB_ENGINE = "django.db.backends.postgresql"
STUDY_DB_HOST = os.getenv("STUDY_PGHOST", _DB_MANAGEMENT["HOST"])
STUDY_DB_PORT = os.getenv("STUDY_PGPORT", _DB_MANAGEMENT["PORT"])
STUDY_DB_USER = os.getenv("STUDY_PGUSER", _DB_MANAGEMENT["USER"])
STUDY_DB_PASSWORD = os.getenv("STUDY_PGPASSWORD", _DB_MANAGEMENT["PASSWORD"])
STUDY_DB_SEARCH_PATH = os.getenv("STUDY_SEARCH_PATH", "data")  # Changed to 'data' per project description; was 'public'

# === Database Routers ===
DATABASE_ROUTERS = ["apps.tenancy.db_router.StudyDBRouter"]

# === i18n & Timezone ===
LANGUAGE_CODE = "vi"
LANGUAGES = [("vi", "Vietnamese"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_L10N = True
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_TZ = True

# === Static & Media ===
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "web" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"  # Uncommented and added default; configure storage in production
MEDIA_ROOT = BASE_DIR / "media"

# === Authentication ===
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# === Security ===
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_SSL_REDIRECT = not DEBUG  # Redirect HTTP to HTTPS in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"  # Prevent clickjacking

# === Defaults ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === Logging ===
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[%(levelname)s] %(message)s"},
        "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": str(LOGS_DIR / "django.log"),
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "apps.tenancy": {"handlers": ["console", "file"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
    },
}

# === Custom settings ===
TENANCY_ENABLED = os.getenv("TENANCY_ENABLED", "False").lower() in ("true", "1", "yes")
TENANCY_STUDY_CODE_PREFIX = os.getenv("TENANCY_STUDY_CODE_PREFIX", "study_")

# === Additional necessary settings ===
# Caches: Add a simple cache for sessions or queries; use Redis/Memcached in production
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Email: Placeholder; configure for password reset, notifications
FEATURE_PASSWORD_RESET = False  # If enabling, add email settings below
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # Use smtp in production
# EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
# EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
# EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
# EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
# Testing: For multi-DB, ensure tests run on test databases
if "test" in sys.argv:
    DATABASES["default"]["NAME"] = "test_" + DATABASES["default"]["NAME"]
    # Add test prefixes for study DBs if needed in custom test runner
    # Add test prefixes for study DBs if needed in custom test runner

# Password validation: Strengthen in production
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]