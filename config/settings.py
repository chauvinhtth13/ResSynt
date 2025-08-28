# config/settings.py (optimized)
import os
import sys
import threading
from pathlib import Path
import environ

# Env setup
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost:8000', '127.0.0.1:8000']),
)
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / ".env")  # Loads .env if exists

# Core settings
SECRET_KEY = env("SECRET_KEY")  # Required
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[]) # type: ignore
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Installed apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "chartjs",
    "parler",
    "apps.web",
    "apps.tenancy.apps.TenancyConfig",
    "apps.studies"
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.tenancy.middleware.NoCacheMiddleware",
    "apps.tenancy.middleware.StudyRoutingMiddleware",
]

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "templates"],
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

# Database: Main management DB
_DB_MANAGEMENT = env.db(
    "DATABASE_URL",
    default=f"postgres://{env('PGUSER', default='postgres')}:{env('PGPASSWORD', default='')}@{env('PGHOST', default='localhost')}:{env('PGPORT', default='5432')}/{env('PGDATABASE', default='db')}", #type: ignore
    engine="django.db.backends.postgresql",
)

_DB_MANAGEMENT.update({
    "CONN_MAX_AGE": 0 if DEBUG else env.int("PG_CONN_MAX_AGE", default=600), #type: ignore
    "CONN_HEALTH_CHECKS": not DEBUG,
    "ATOMIC_REQUESTS": False,
    "AUTOCOMMIT": True,
    "OPTIONS": {
        "options": "-c search_path=metadata,public",
        "sslmode": "disable" if DEBUG else "require",
    },
    "TIME_ZONE": env("DB_TIME_ZONE", default="Asia/Ho_Chi_Minh"), #type: ignore
})

DATABASES = {
    "default": _DB_MANAGEMENT,
}

# Per-study DB template
STUDY_DB_AUTO_REFRESH_SECONDS = env("STUDY_DB_AUTO_REFRESH_SECONDS", cast=int, default=300) # type: ignore
STUDY_DB_PREFIX = env("STUDY_DB_PREFIX", default="db_study_") # type: ignore
STUDY_DB_ENGINE = "django.db.backends.postgresql"
STUDY_DB_HOST = env("STUDY_PGHOST", default=_DB_MANAGEMENT.get("HOST", "localhost"))
STUDY_DB_PORT = env("STUDY_PGPORT", default=_DB_MANAGEMENT.get("PORT", "5432"))
STUDY_DB_USER = env("STUDY_PGUSER", default=_DB_MANAGEMENT.get("USER"))
STUDY_DB_PASSWORD = env("STUDY_PGPASSWORD", default=_DB_MANAGEMENT.get("PASSWORD"))
STUDY_DB_SEARCH_PATH = env("STUDY_SEARCH_PATH", default="data") # type: ignore

# Database Routers
DATABASE_ROUTERS = ["apps.tenancy.db_router.StudyDBRouter"]

# i18n & Timezone
LANGUAGE_CODE = "vi"
LANGUAGES = [("vi", "Vietnamese"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_L10N = True
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_TZ = True

PARLER_LANGUAGES = {
    None: (
        {"code": "en"},
        {"code": "vi"},
    ),
    "default": {
        "fallbacks": ["vi"],
        "hide_untranslated": False,
    },
}

# Static & Media
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "web" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Authentication
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
FEATURE_PASSWORD_RESET = env("FEATURE_PASSWORD_RESET", cast=bool, default=False) # type: ignore

# Security (conditional on DEBUG: disabled in dev, enabled in prod)
SESSION_ENGINE = "django.contrib.sessions.backends.cache" if not DEBUG else "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000  # 0 disables HSTS in dev
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_BROWSER_XSS_FILTER = True

# Defaults
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging
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
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "level": "DEBUG" if DEBUG else "INFO",
            "delay": True,
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
        "django.utils.autoreload": {
            "handlers": ["console", "file"],
            "level": "INFO",
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

# Caches
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache" if not DEBUG else "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1") if not DEBUG else "unique-snowflake", # type: ignore
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient" if not DEBUG else None,
        },
    }
}

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" if FEATURE_PASSWORD_RESET else "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com") # type: ignore
EMAIL_PORT = env("EMAIL_PORT", cast=int, default=587) # type: ignore
EMAIL_USE_TLS = env("EMAIL_USE_TLS", cast=bool, default=True) # type: ignore
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="") # type: ignore
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="") # type: ignore

# Custom settings
TENANCY_ENABLED = env("TENANCY_ENABLED", cast=bool, default=True) # type: ignore
TENANCY_STUDY_CODE_PREFIX = env("TENANCY_STUDY_CODE_PREFIX", default="study_") # type: ignore

# Thread-local
THREAD_LOCAL = threading.local()

# Testing
if "test" in sys.argv:
    DATABASES["default"]["NAME"] = "test_" + DATABASES["default"]["NAME"]
    TEST_RUNNER = "apps.tenancy.test_runner.StudyTestRunner"

# Password validation
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]