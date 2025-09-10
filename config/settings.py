# config/settings.py (OPTIMIZED)
"""
Django settings module for the project.

This file contains all configuration settings for the Django application,
including database connections, security options, middleware, and custom
application-specific settings. It uses environment variables for flexibility
and security.

Environment variables are loaded from a .env file if present, otherwise
fallback to system environment variables.

Note: This file is optimized for performance in production while maintaining
debug capabilities in development. Always review and update settings based
on deployment environment.
"""

import threading
import environ
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variable management using django-environ.
env = environ.Env()

# Read .env file if it exists.
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)
else:
    print(f"Warning: {env_file} not found. Using environment variables.")

# Core Security Settings
# ----------------------
# SECRET_KEY is used for cryptographic signing. Keep this secret in production.
SECRET_KEY = env("SECRET_KEY")

# Debug and Host Settings
# -----------------------
# DEBUG mode enables detailed error pages and disables optimizations.
DEBUG = env("DEBUG")
# ALLOWED_HOSTS specifies which hosts/domains can serve the app.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
# CSRF_TRUSTED_ORIGINS for secure cross-origin requests.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # type: ignore

# URL Configuration
# -----------------
# ROOT_URLCONF points to the root URL configuration.
ROOT_URLCONF = "config.urls"
# WSGI_APPLICATION for WSGI deployment.
WSGI_APPLICATION = "config.wsgi.application"
# ASGI_APPLICATION for ASGI deployment (e.g., with channels).
ASGI_APPLICATION = "config.asgi.application"

# Application Definition
# ----------------------
# List of installed Django apps and third-party packages.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "axes",
    "chartjs",
    "parler",
    'backend.tenancy',
    'backend.api',
    "backend.studies",
]

# Middleware
# ----------
# Middleware stack processes requests and responses globally.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Optimized custom middleware for tenancy and performance.
    "backend.tenancy.middleware.SecurityHeadersMiddleware",
    "backend.tenancy.middleware.PerformanceMonitoringMiddleware",
    "backend.tenancy.middleware.StudyRoutingMiddleware",
    "backend.tenancy.middleware.CacheControlMiddleware",
    "backend.tenancy.middleware.DatabaseConnectionCleanupMiddleware",
]

# Templates
# ---------
# Configuration for Django's template engine.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
            "debug": DEBUG,
        },
    },
]

# Enable template caching in production for performance.
if not DEBUG:
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        ("django.template.loaders.cached.Loader", [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]),
    ]

# Database Configuration
# ----------------------
class DatabaseConfig:
    """
    Centralized database configuration class.

    Provides methods to configure management and study databases with
    optimizations for connection pooling, timeouts, and security.
    Validates and falls back to environment variables if needed.
    """

    @staticmethod
    def get_management_db():
        """
        Get configuration for the management database.

        Supports DATABASE_URL or individual PG* variables.
        Optimizes for production with connection pooling and health checks.
        """
        db_url = env("DATABASE_URL")

        if db_url:
            config = env.db("DATABASE_URL")
        else:
            config = {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": env("PGDATABASE"),
                "USER": env("PGUSER"),
                "PASSWORD": env("PGPASSWORD"),
                "HOST": env("PGHOST"),
                "PORT": env.int("PGPORT"),
            }

        # Connection pooling and optimization settings.
        config.update({
            "CONN_MAX_AGE": 0 if DEBUG else 600,  # 10 min connection reuse in production.
            "CONN_HEALTH_CHECKS": not DEBUG,
            "ATOMIC_REQUESTS": False,  # Avoid wrapping every request in a transaction for performance.
            "AUTOCOMMIT": True,
            "OPTIONS": {
                "options": "-c search_path=management,public",
                "sslmode": "disable" if DEBUG else "require",
                "connect_timeout": 10,
                "client_encoding": "UTF8",
                # PostgreSQL keepalive settings to prevent connection drops.
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
            "TIME_ZONE": env("TIME_ZONE"),
        })

        # Add advanced connection pooling in production.
        if not DEBUG:
            config["OPTIONS"].update({
                "pool": True,  # Enable connection pooling.
                "pool_size": 10,  # Minimum number of connections to maintain.
                "max_overflow": 20,  # Maximum additional connections on demand.
                "pool_recycle": 3600,  # Recycle connections after 1 hour to prevent leaks.
                "pool_pre_ping": True,  # Verify connections before use.
            })

        return config

    @staticmethod
    def get_study_db_config(db_name: str):
        """
        Get configuration for a study-specific database.

        Uses environment variables for study DB credentials.
        Optimized with shorter connection ages and timeouts for dynamic tenants.
        """
        return {
            "ENGINE": env("STUDY_DB_ENGINE"),
            "NAME": db_name,
            "USER": env("STUDY_PGUSER"),
            "PASSWORD": env("STUDY_PGPASSWORD"),
            "HOST": env("STUDY_PGHOST"),
            "PORT": env.int("STUDY_PGPORT"),
            "CONN_MAX_AGE": 0 if DEBUG else 300,  # 5 min for study DBs in production.
            "CONN_HEALTH_CHECKS": True,
            "ATOMIC_REQUESTS": False,
            "OPTIONS": {
                "options": f"-c search_path={env('STUDY_DB_SEARCH_PATH')},public",
                "sslmode": "disable" if DEBUG else "require",
                "connect_timeout": 5,
                "statement_timeout": "30000",  # 30 seconds timeout for queries.
                "idle_in_transaction_session_timeout": "60000",  # 60 seconds for idle transactions.
            },
        }

# Database dictionary with default (management) DB.
DATABASES = {
    "default": DatabaseConfig.get_management_db()
}

# Ensure search path is set for default DB.
DATABASES["default"]["OPTIONS"]["options"] = "-c search_path=management,public"

# Database Routers
# ----------------
# Routers for multi-database (tenancy) setup.
DATABASE_ROUTERS = ['backend.tenancy.db_router.TenantRouter']

# Study Database Settings
# -----------------------
# Prefix for study database names and engine.
STUDY_DB_PREFIX = env("STUDY_DB_PREFIX")
STUDY_DB_ENGINE = env("STUDY_DB_ENGINE")

# Custom User Model
# -----------------
# Overrides Django's default User model with tenancy-aware version.
AUTH_USER_MODEL = 'tenancy.User'

# Internationalization
# --------------------
# Language and timezone settings.
LANGUAGE_CODE = env("DEFAULT_LANGUAGE")
LANGUAGES = [
    ("vi", "Tiếng Việt"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = env("TIME_ZONE")
DATE_FORMAT = env("DATE_FORMAT")
TIME_FORMAT = env("TIME_FORMAT")
DATETIME_FORMAT = env("DATETIME_FORMAT")
USE_TZ = True

# Parler settings for multilingual models.
PARLER_DEFAULT_LANGUAGE_CODE = 'en'
PARLER_LANGUAGES = {
    None: (
        {'code': 'en', 'name': 'English'},
        {'code': 'vi', 'name': 'Tiếng Việt'},
    ),
    'default': {
        'fallbacks': ['en'],
        'hide_untranslated': False,
    }
}

# Static Files
# ------------
# Settings for serving static files (CSS, JS, images).
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"]  # Directory for static files in frontend.
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Use manifest storage in production for cache-busting.
if not DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Media Files
# -----------
# Settings for user-uploaded files.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Authentication Redirects
# ------------------------
# URLs for login, logout, and redirects.
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
# Feature flag for password reset functionality.
FEATURE_PASSWORD_RESET = env.bool("FEATURE_PASSWORD_RESET")

# Security Settings
# -----------------
# Environment-aware security enhancements.
SESSION_ENGINE = "django.contrib.sessions.backends.cache" if not DEBUG else "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour session lifetime.
SESSION_SAVE_EVERY_REQUEST = False  # Save only when session is modified.
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000  # 1 year HSTS in production.
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_BROWSER_XSS_FILTER = True

# Additional production security policies.
if not DEBUG:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    CSRF_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_SAMESITE = "Strict"

# Default Primary Key Field Type
# ------------------------------
# Use BigAutoField for all models by default.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging Configuration
# ---------------------
# Optimized logging with rotation and minimal overhead.
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "WARNING",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "simple",
            "filename": str(LOGS_DIR / "django.log"),
            "encoding": "utf-8",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB per file.
            "backupCount": 3,
            "level": "WARNING",
            "delay": True,  # Delay file creation until first log.
        },
        "axes_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "simple",
            "filename": str(LOGS_DIR / "axes.log"),
            "encoding": "utf-8",
            "maxBytes": 2 * 1024 * 1024,  # 2 MB per file.
            "backupCount": 2,
            "level": "WARNING",
            "delay": True,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "backend.tenancy": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "backend.studies": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "axes": {
            "handlers": ["axes_file", "console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Caching Configuration
# ---------------------
# Use local memory cache in debug, Redis in production.
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
            "OPTIONS": {
                "MAX_ENTRIES": 1000,
                "CULL_FREQUENCY": 3,  # Cull 1/3 of cache when full.
            }
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "retry_on_timeout": True,
                },
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                "IGNORE_EXCEPTIONS": True,  # Graceful failure if Redis is unavailable.
            },
            "KEY_PREFIX": "ressync",
            "VERSION": 1,
        }
    }

# Cache middleware settings.
CACHE_MIDDLEWARE_SECONDS = 300 if not DEBUG else 0
CACHE_MIDDLEWARE_KEY_PREFIX = 'ressync'

# Email Configuration
# -------------------
# SMTP settings for password reset if enabled.
if FEATURE_PASSWORD_RESET:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env.int("EMAIL_PORT")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

    # Validate required settings in production.
    if not DEBUG and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
        raise ValueError("EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required when FEATURE_PASSWORD_RESET is True")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Custom Settings
# ---------------
# Tenancy-related feature flags and prefixes.
TENANCY_ENABLED = env.bool("TENANCY_ENABLED")
TENANCY_STUDY_CODE_PREFIX = env("TENANCY_STUDY_CODE_PREFIX")

# Thread-local storage for request-scoped data.
THREAD_LOCAL = threading.local()

# Authentication Backends
# -----------------------
# Backends for authentication, including Axes for brute-force protection.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # For django-axes 8.0.0
    'django.contrib.auth.backends.ModelBackend',
]

# Axes Configuration
# ------------------
# Settings for django-axes to prevent brute-force login attempts.
AXES_FAILURE_LIMIT = 8  # Number of failed attempts before lockout.
AXES_COOLOFF_TIME = None  # Hours to wait after lockout.
AXES_RESET_ON_SUCCESS = True  # Reset counter on successful login.
AXES_LOCKOUT_PARAMETERS = [['username']]  # Lock by username only.
AXES_USERNAME_FORM_FIELD = 'username'
AXES_HANDLER = 'axes.handlers.database.AxesDatabaseHandler'
AXES_CACHE = 'default'
AXES_ENABLED = True  # Disable in debug if needed by setting to False.
AXES_VERBOSE = DEBUG

# Password Hashers
# ----------------
# Preferred hashers for secure password storage.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Password Validation
# --------------------
# Validators to enforce strong passwords.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]