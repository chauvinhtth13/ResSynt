import os
import sys
import threading  # Added for thread-local
from pathlib import Path
from dotenv import load_dotenv

# === Paths & .env ===
BASE_DIR = Path(__file__).resolve().parent.parent  # -> ResSync/
load_dotenv(BASE_DIR / ".env")  # Load .env from project root

# === Core settings ===
SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in .env; no default for security
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in .env")
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
    'rosetta',
    'parler',
    # ResSync apps
    "apps.web",
    "apps.tenancy.apps.TenancyConfig",
    #"apps.studies",  # Added: For tenant-specific models (per-study data)
]

# === Middleware ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.tenancy.middleware.NoCacheMiddleware',  # Add this new one
    'apps.tenancy.middleware.StudyRoutingMiddleware',  # Existing
]

# === Templates ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "templates"],  # Corrected path based on folder structure
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
    "USER": os.getenv("PGUSER", "ressync_admin"),
    "PASSWORD": os.getenv("PGPASSWORD"),
    "HOST": os.getenv("PGHOST", "localhost"),
    "PORT": os.getenv("PGPORT", "5432"),
    "OPTIONS": {
        "options": "-c search_path=metadata,public",
        "sslmode": "disable" if DEBUG else "require",  # Enforce SSL for security
    },
    "CONN_MAX_AGE": int(os.getenv("PG_CONN_MAX_AGE", "600")),
    "CONN_HEALTH_CHECKS": not DEBUG,  # Enable in production
    "ATOMIC_REQUESTS": False,  # Set True in production if needed
    "AUTOCOMMIT": True,
    "TIME_ZONE": os.getenv("DB_TIME_ZONE", "Asia/Ho_Chi_Minh"),
}

DATABASES = {
    "default": _DB_MANAGEMENT,  # Alias for db_management
    "db_management": _DB_MANAGEMENT,
}

# === Template for per-study DBs (dynamic loading in db_loader.py) ===
STUDY_DB_AUTO_REFRESH_SECONDS = int(os.getenv("STUDY_DB_AUTO_REFRESH_SECONDS", "300"))
STUDY_DB_PREFIX = os.getenv("STUDY_DB_PREFIX", "db_study_")
STUDY_DB_ENGINE = "django.db.backends.postgresql"
STUDY_DB_HOST = os.getenv("STUDY_PGHOST", _DB_MANAGEMENT["HOST"])
STUDY_DB_PORT = os.getenv("STUDY_PGPORT", _DB_MANAGEMENT["PORT"])
STUDY_DB_USER = os.getenv("STUDY_PGUSER", _DB_MANAGEMENT["USER"])
STUDY_DB_PASSWORD = os.getenv("STUDY_PGPASSWORD", _DB_MANAGEMENT["PASSWORD"])
STUDY_DB_SEARCH_PATH = os.getenv("STUDY_SEARCH_PATH", "data")  # Matches project schema 'data'

# === Database Routers ===
DATABASE_ROUTERS = [
    "apps.tenancy.db_router.StudyDBRouter",  # Custom router for study DBs
]

# === i18n & Timezone ===
LANGUAGE_CODE = "vi"
LANGUAGES = [("vi", "Vietnamese"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_TZ = True  # Required for TIMESTAMPTZ handling

PARLER_LANGUAGES = {
    None: (
        {'code': 'en',}, # English
        {'code': 'vi',}, # Vietnamese
    ),
    'default': {
        'fallbacks': ['vi'],
        'hide_untranslated': False,
    }
}

# === Static & Media ===
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "static"]  # Corrected path based on folder structure
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# === Authentication ===
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = '/select-study/'
LOGOUT_REDIRECT_URL = "/accounts/login/"
FEATURE_PASSWORD_RESET = os.getenv("FEATURE_PASSWORD_RESET", "False").lower() in ("true", "1", "yes")

# === Security ===
SESSION_COOKIE_SECURE = not DEBUG  # Enable in production
CSRF_COOKIE_SECURE = not DEBUG  # Enable in production
SECURE_SSL_REDIRECT = not DEBUG  # Redirect HTTP to HTTPS in production
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 year for HSTS in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # For proxy setups
X_FRAME_OPTIONS = "DENY"

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
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG" if DEBUG else "WARNING",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": str(LOGS_DIR / "django.log"),
            "encoding": "utf-8",
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 5,
            "level": "DEBUG" if DEBUG else "INFO",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "apps.tenancy": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "apps.web": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# === Caches ===
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache" if not DEBUG else "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/1") if not DEBUG else "unique-snowflake",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient" if not DEBUG else None,
        },
    }
}

# === Email ===
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" if FEATURE_PASSWORD_RESET else "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

# === Custom settings ===
TENANCY_ENABLED = os.getenv("TENANCY_ENABLED", "True").lower() in ("true", "1", "yes")
TENANCY_STUDY_CODE_PREFIX = os.getenv("TENANCY_STUDY_CODE_PREFIX", "study_")

# Thread-local for current study (used in middleware and router)
THREAD_LOCAL = threading.local()

# === Testing ===
if "test" in sys.argv:
    DATABASES["default"]["NAME"] = "test_" + DATABASES["default"]["NAME"]
    TEST_RUNNER = "apps.tenancy.test_runner.StudyTestRunner"

# === Password validation ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

TAILWIND_APP_NAME = "theme"  # Tailwind app name for static files