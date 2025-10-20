# config/settings.py (FINAL OPTIMIZED VERSION - CLEANED)
"""
Optimized Django settings for ResSync Database-per-Study Platform
With proper schema configuration for study databases
"""

import environ
import sys
from pathlib import Path
from typing import Dict
from django.utils.translation import gettext_lazy as _
import logging

# Setup logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# BASE CONFIGURATION
# ==========================================

# Environment setup
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    DEBUG=(bool, False),
    TENANCY_ENABLED=(bool, True),
    FEATURE_PASSWORD_RESET=(bool, False),
)

env_file = BASE_DIR / ".env"
environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")  # type: ignore

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ==========================================
# STUDY DATABASE CONFIGURATION
# ==========================================
# STUDY_DB_PREFIX = env("STUDY_DB_PREFIX")
# STUDY_DB_SCHEMA = env("STUDY_DB_SCHEMA")

# ==========================================
# INSTALLED APPS
# ==========================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "axes",
    "parler",
]

BASE_LOCAL_APPS = [
    "backends.tenancy",
    "backends.api",
    "backends.studies",
]

# ==========================================
# DATEBASE CONFIGURATION CLASS 
# ==========================================

STUDY_DB_SCHEMA = env("STUDY_DB_SCHEMA")
STUDY_DB_PREFIX = env("STUDY_DB_PREFIX")

# ==========================================
# LOAD STUDY APPS SAFELY
# ==========================================


def load_study_apps() -> tuple:
    """
    Load study apps with comprehensive error handling
    
    Returns:
        Tuple of (study_apps: List[str], has_errors: bool)
    """
    import sys
    
    # Check if we're in a management command
    is_management_command = 'manage.py' in sys.argv[0] if sys.argv else False
    
    try:
        from backends.studies.study_loader import get_loadable_apps
        
        # Get study apps
        study_apps = get_loadable_apps()
        
        if study_apps:
            return study_apps, False
        else:
            return [], False

    except Exception as e:
        logger.error("ERROR: Failed to load study apps")
        logger.error(f"Error: {e}")
        
        import traceback
        logger.debug(traceback.format_exc())
        
        return [], True

STUDY_APPS, HAS_STUDY_ERRORS = load_study_apps()

# Combine all apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + BASE_LOCAL_APPS + STUDY_APPS

logger.info(f"List installed: {INSTALLED_APPS}")

# ==========================================
# DATABASE CONFIGURATION
# ==========================================

class DatabaseConfig:
    """Database configuration"""

    REQUIRED_KEYS = {
        "ENGINE",
        "NAME",
        "USER",
        "PASSWORD",
        "HOST",
        "PORT",
        "ATOMIC_REQUESTS",
        "AUTOCOMMIT",
        "CONN_MAX_AGE",
        "CONN_HEALTH_CHECKS",
        "TIME_ZONE",
        "OPTIONS",
        "TEST",
    }

    @classmethod
    def get_base_config(cls) -> Dict:
        """Get base connection info"""
        # Option 1: Use DATABASE_URL (recommended for Heroku, Railway, etc.)
        # db_url = env("DATABASE_URL")

        # if db_url:
        #     return env.db("DATABASE_URL")

        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("PGDATABASE"),
            "USER": env("PGUSER"),
            "PASSWORD": env("PGPASSWORD"),
            "HOST": env("PGHOST"),
            "PORT": env.int("PGPORT"),
        }

    @classmethod
    def add_default_settings(cls, config: Dict, conn_max_age: int = 0) -> Dict:
        """Add required Django settings"""
        config.update(
            {
                "ATOMIC_REQUESTS": False,
                "AUTOCOMMIT": True,
                "CONN_MAX_AGE": conn_max_age,
                "CONN_HEALTH_CHECKS": True,
                "TIME_ZONE": None,
                "OPTIONS": {},
                "TEST": {
                    "CHARSET": None,
                    "COLLATION": None,
                    "NAME": None,
                    "MIRROR": None,
                },
            }
        )
        return config

    @classmethod
    def get_options(cls, schema: str, connect_timeout: int, sslmode: str) -> Dict:
        """Get common OPTIONS dict"""
        return {
            "options": f"-c search_path={schema},public",
            "sslmode": sslmode,
            "connect_timeout": connect_timeout,
            "prepare_threshold": None,
            "cursor_factory": None,
        }

    @classmethod
    def get_management_db(cls) -> Dict:
        """Management database config"""
        config = cls.get_base_config()
        conn_max_age = 0 if DEBUG else 600
        config = cls.add_default_settings(config, conn_max_age)

        sslmode = "disable" if DEBUG else "require"
        config["OPTIONS"] = cls.get_options(str(env("PGSCHEMA")), 10, sslmode)

        cls.validate_config(config, "management")
        return config

    @classmethod
    def get_study_db_config(cls, db_name: str) -> Dict:
        """Study database config"""
        main_db = cls.get_management_db()

        config = {
            "ENGINE": main_db["ENGINE"],
            "NAME": db_name,
            "USER": env("STUDY_PGUSER", default=main_db["USER"]),
            "PASSWORD": env("STUDY_PGPASSWORD", default=main_db["PASSWORD"]),
            "HOST": env("STUDY_PGHOST", default=main_db["HOST"]),
            "PORT": env.int("STUDY_PGPORT", default=main_db["PORT"]),
        }

        conn_max_age = 0 if DEBUG else 300
        config = cls.add_default_settings(config, conn_max_age)

        config["OPTIONS"] = cls.get_options(
            str(env("STUDY_DB_SCHEMA")), 5, main_db["OPTIONS"]["sslmode"]
        )

        cls.validate_config(config, db_name)
        return config

    @classmethod
    def validate_config(cls, config: Dict, db_name: str = "default") -> None:
        """Validate config"""
        missing = cls.REQUIRED_KEYS - set(config.keys())
        if missing:
            raise ValueError(f"Database '{db_name}' missing keys: {sorted(missing)}")
        


# ==========================================
# INITIALIZE DATABASES
# ==========================================

# Start with management database only
DATABASES = {
    "default": DatabaseConfig.get_management_db(),
}

# Validate
DatabaseConfig.validate_config(DATABASES["default"], "default")

try:
    from backends.studies.study_loader import get_study_databases

    study_databases = get_study_databases()

    if study_databases:
        DATABASES.update(study_databases)
        logger.debug(f"Configured {len(study_databases)} study database(s)")
except Exception as e:
    logger.error(f"Error configuring databases: {e}")

# Database router
DATABASE_ROUTERS = ["backends.tenancy.db_router.TenantRouter"]

# ==========================================
# MIDDLEWARE (OPTIMIZED ORDER)
# ==========================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "backends.tenancy.middleware.UnifiedTenancyMiddleware",
    #'backends.tenancy.signals.StudyDatabaseTrackingMiddleware',
    "axes.middleware.AxesMiddleware",
    "backends.tenancy.middleware.AxesNoRedirectMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==========================================
# TEMPLATES (WITH CONTEXT PROCESSORS)
# ==========================================
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
                "backends.studies.study_43en.services.context_processors.study_context",
            ],
        },
    },
]

# Use cached template loader in production for better performance
if not DEBUG:
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

# ==========================================
# CACHING (OPTIMIZED)
# ==========================================
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "resync-cache",
        }
    }
else:
    redis_url = env("REDIS_URL")
    if redis_url:
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": redis_url,
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "IGNORE_EXCEPTIONS": True,
                    "CONNECTION_POOL_CLASS_KWARGS": {
                        "max_connections": 50,
                        "timeout": 20,
                    },
                },
            }
        }
    else:
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.db.DatabaseCache",
                "LOCATION": "django_cache_table",
            }
        }

# Cache middleware configuration
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = "resync"

# ==========================================
# SESSION CONFIGURATION
# ==========================================
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 7200  # 2 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = False

# ==========================================
# AUTHENTICATION & AXES
# ==========================================
AUTH_USER_MODEL = "tenancy.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # ← Thêm dòng này
    "backends.tenancy.contrib.auth.BlockedUserBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Axes configuration for brute-force protection
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = None  # No auto-unlock
AXES_LOCKOUT_PARAMETERS = ["username"]  # Username only, NOT IP
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_AT_FAILURE = True
AXES_LOCKOUT_TEMPLATE = None  # No redirect
AXES_LOCKOUT_CALLABLE = "backends.api.base.lockout.custom_lockout_handler"
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_CACHE_BACKEND = "default"

AXES_VERBOSE = not DEBUG
AXES_ENABLE_ACCESS_FAILURE_LOG = True  # Log tất cả failures
AXES_DISABLE_ACCESS_LOG = False  # Giữ access log

# ==========================================
# INTERNATIONALIZATION
# ==========================================
USE_I18N = True
USE_TZ = True

# Default language - Vietnamese
LANGUAGE_CODE = "vi"

# Available languages
LANGUAGES = [
    ("vi", _("Vietnamese")),  # Vietnamese first
    ("en", _("English")),  # English second
]

# Language cookie settings
LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60  # 1 year
LANGUAGE_COOKIE_DOMAIN = None
LANGUAGE_COOKIE_PATH = "/"
LANGUAGE_COOKIE_SECURE = not DEBUG  # Automatically secure in production
LANGUAGE_COOKIE_HTTPONLY = False
LANGUAGE_COOKIE_SAMESITE = "Lax"

# Language session key
LANGUAGE_SESSION_KEY = "_language"

# Locale paths - where translation files are stored
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Time zone - Vietnam
TIME_ZONE = "Asia/Ho_Chi_Minh"

# Vietnamese date/time formats
DATE_FORMAT = "d/m/Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = "d/m/Y H:i:s"
YEAR_MONTH_FORMAT = "m/Y"
MONTH_DAY_FORMAT = "d/m"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"

# Input formats for forms (Vietnamese style)
DATE_INPUT_FORMATS = [
    "%d/%m/%Y",  # '25/09/2025'
    "%d-%m-%Y",  # '25-09-2025'
    "%d.%m.%Y",  # '25.09.2025'
    "%Y-%m-%d",  # '2025-09-25' (ISO)
]

TIME_INPUT_FORMATS = [
    "%H:%M:%S",  # '14:30:59'
    "%H:%M",  # '14:30'
    "%H-%M-%S",  # '14-30-59'
    "%H-%M",  # '14-30'
]

DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",  # ISO
    "%Y-%m-%d %H:%M",
]

# Number formats (Vietnamese style)
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
NUMBER_GROUPING = 3

# First day of week (Monday)
FIRST_DAY_OF_WEEK = 1

# Parler configuration for multi-language models
PARLER_DEFAULT_LANGUAGE_CODE = "vi"
PARLER_LANGUAGES = {
    None: (
        {"code": "vi"},  # Vietnamese first
        {"code": "en"},
    ),
    "default": {
        "fallbacks": ["vi", "en"],  # Fallback to Vietnamese first
        "hide_untranslated": False,
    },
}

# ==========================================
# STATIC & MEDIA FILES
# ==========================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontends" / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Use manifest static files storage in production for cache busting
if not DEBUG:
    STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    )

# ==========================================
# SECURITY SETTINGS
# ==========================================
if not DEBUG:
    # HTTPS settings
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Security headers
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ==========================================
# LOGGING CONFIGURATION
# ==========================================
# Ensure logs directory exists
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} | {name} | {module}.{funcName}:{lineno} | {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{levelname}] {asctime} | {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "console_minimal": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        # Console - chỉ WARNING trở lên
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console_minimal",
            "level": "ERROR",  # Chỉ ERROR + CRITICAL
        },
        # All logs - file tổng hợp
        "file_all": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "all.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "DEBUG",
        },
        # Error logs - chỉ ERROR trở lên
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "ERROR",
        },
        # Database queries
        "file_db": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "database.log",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "verbose",
            "level": "DEBUG" if DEBUG else "INFO",
        },
        # Security logs
        "file_security": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "security.log",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "WARNING",
        },
    },
    # Root logger - handlers chính
    "root": {
        "handlers": ["console", "file_all", "file_error"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
    "loggers": {
        # Django core - sử dụng propagate để tận dụng root handlers
        "django": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        # Database queries - handler riêng
        "django.db.backends": {
            "handlers": ["file_db"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Django request/response - chỉ log ERROR
        "django.request": {
            "handlers": ["file_error"],
            "level": "ERROR",
            "propagate": True,  # Cũng đẩy lên root
        },
        # Security events - handler riêng
        "django.security": {
            "handlers": ["file_security"],
            "level": "WARNING",
            "propagate": True,
        },
        # App backends.tenancy - sử dụng root handlers
        "backends.tenancy": {
            "handlers": [],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
        # App backends.studies - sử dụng root handlers
        "backends.studies": {
            "handlers": [],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
        # Logger cho settings.py (config.settings)
        "config.settings": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        # Silence verbose third-party packages
        "environ": {
            "handlers": [],
            "level": "WARNING",
            "propagate": True,
        },
    },
}

# ==========================================
# OTHER SETTINGS
# ==========================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication URLs
LOGIN_URL = "/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/"

# Organization settings
ORGANIZATION_NAME = env("ORGANIZATION_NAME")
PLATFORM_VERSION = env("PLATFORM_VERSION")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
