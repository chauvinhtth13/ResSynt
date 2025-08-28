# config/settings.py (FIXED)
import os
import sys
import threading
from pathlib import Path
from django.utils.translation import gettext_lazy as _

# Import django-environ with error handling
try:
    import environ
except ImportError:
    raise ImportError(
        "django-environ is required. Install with: pip install django-environ"
    )

# Environment setup
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CSRF_TRUSTED_ORIGINS=(list, []),
)

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)
else:
    print(f"Warning: {env_file} not found. Using environment variables.")

# Core Security Settings
SECRET_KEY = env("SECRET_KEY")
if not isinstance(SECRET_KEY, str) or len(SECRET_KEY) < 50:
    raise ValueError(
        "SECRET_KEY must be set and at least 50 characters long. "
        "Generate with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[]) # pyright: ignore[reportArgumentType]

# URL Configuration
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Application definition
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

# Database configuration with proper fallback
def get_database_config():
    """Get database configuration with validation."""
    db_url = env("DATABASE_URL", default=None)  # pyright: ignore[reportArgumentType]
    
    if db_url:
        db_config = env.db("DATABASE_URL")
    else:
        # Fallback to individual settings
        db_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("PGDATABASE", default="db_management"), # pyright: ignore[reportArgumentType]
            "USER": env("PGUSER", default="postgres"), # pyright: ignore[reportArgumentType]
            "PASSWORD": env("PGPASSWORD", default="" if DEBUG else None), # pyright: ignore[reportArgumentType]
            "HOST": env("PGHOST", default="localhost"), # pyright: ignore[reportArgumentType]
            "PORT": env("PGPORT", default="5432"), # pyright: ignore[reportArgumentType]
        }
        
        # Validate password in production
        if not DEBUG and not db_config["PASSWORD"]:
            raise ValueError("PGPASSWORD is required in production")
    
    # Add connection pool settings
    db_config.update({
        "CONN_MAX_AGE": 0 if DEBUG else env.int("PG_CONN_MAX_AGE", default=600), # pyright: ignore[reportArgumentType]
        "CONN_HEALTH_CHECKS": not DEBUG,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "OPTIONS": {
            "options": "-c search_path=metadata,public",
            "sslmode": "disable" if DEBUG else "require",
            "connect_timeout": 10,
        },
        "TIME_ZONE": env("DB_TIME_ZONE", default="Asia/Ho_Chi_Minh"), # pyright: ignore[reportArgumentType]
    })
    
    return db_config

DATABASES = {
    "default": get_database_config()
}

# Study Database Settings
STUDY_DB_AUTO_REFRESH_SECONDS = env.int("STUDY_DB_AUTO_REFRESH_SECONDS", default=300) # pyright: ignore[reportArgumentType]
STUDY_DB_PREFIX = env("STUDY_DB_PREFIX", default="db_study_") # pyright: ignore[reportArgumentType]
STUDY_DB_ENGINE = env("STUDY_DB_ENGINE", default="django.db.backends.postgresql") # pyright: ignore[reportArgumentType]

# Study DB connection settings (with fallback to management DB settings)
STUDY_DB_HOST = env("STUDY_PGHOST", default=DATABASES["default"].get("HOST", "localhost"))
STUDY_DB_PORT = env("STUDY_PGPORT", default=DATABASES["default"].get("PORT", "5432"))
STUDY_DB_USER = env("STUDY_PGUSER", default=DATABASES["default"].get("USER", "postgres"))
STUDY_DB_PASSWORD = env("STUDY_PGPASSWORD", default=DATABASES["default"].get("PASSWORD", ""))
STUDY_DB_SEARCH_PATH = env("STUDY_SEARCH_PATH", default="data") # pyright: ignore[reportArgumentType]

# Validate study DB password in production
if not DEBUG and not STUDY_DB_PASSWORD:
    raise ValueError("STUDY_PGPASSWORD is required in production")

# Database Routers
DATABASE_ROUTERS = ["apps.tenancy.db_router.StudyDBRouter"]

# Internationalization
LANGUAGE_CODE = "vi"  # Default language
LANGUAGES = [
    ("vi", _("Tiếng Việt")),
    ("en", _("English")),
]
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

# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "web" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Authentication
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
FEATURE_PASSWORD_RESET = env.bool("FEATURE_PASSWORD_RESET", default=False) # pyright: ignore[reportArgumentType]

# Security Settings (environment-aware)
SESSION_ENGINE = "django.contrib.sessions.backends.db" if DEBUG else "django.contrib.sessions.backends.cache"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_BROWSER_XSS_FILTER = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration
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

# Cache Configuration (environment-aware)
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
else:
    # Production uses Redis
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"), # pyright: ignore[reportArgumentType]
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": 50},
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            },
        }
    }

# Email Configuration
if FEATURE_PASSWORD_RESET:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com") # pyright: ignore[reportArgumentType]
    EMAIL_PORT = env.int("EMAIL_PORT", default=587) # pyright: ignore[reportArgumentType]
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True) # pyright: ignore[reportArgumentType]
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    
    # Validate email settings in production
    if not DEBUG and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
        raise ValueError("EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required when FEATURE_PASSWORD_RESET is True")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Custom Settings
TENANCY_ENABLED = env.bool("TENANCY_ENABLED", default=True) # pyright: ignore[reportArgumentType]
TENANCY_STUDY_CODE_PREFIX = env("TENANCY_STUDY_CODE_PREFIX", default="study_") # pyright: ignore[reportArgumentType]
 
# Thread-local storage
THREAD_LOCAL = threading.local()

# Test Configuration
if "test" in sys.argv:
    DATABASES["default"]["NAME"] = "test_" + DATABASES["default"]["NAME"]
    TEST_RUNNER = "apps.tenancy.test_runner.StudyTestRunner"
    # Use faster password hasher for tests
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
else:
    # Production password hashers
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.Argon2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
        "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    ]

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]