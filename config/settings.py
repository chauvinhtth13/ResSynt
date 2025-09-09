# config/settings.py (OPTIMIZED)
import threading
import environ
from pathlib import Path


# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment setup
env = environ.Env()

# Read .env file
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)
else:
    print(f"Warning: {env_file} not found. Using environment variables.")

# Core Security Settings
SECRET_KEY = env("SECRET_KEY")

# Debug and Host Settings
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS") 
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[]) # type: ignore

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
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Optimized custom middleware
    "backend.tenancy.middleware.SecurityHeadersMiddleware",
    "backend.tenancy.middleware.PerformanceMonitoringMiddleware",
    "backend.tenancy.middleware.StudyRoutingMiddleware",
    "backend.tenancy.middleware.CacheControlMiddleware",
    "backend.tenancy.middleware.DatabaseConnectionCleanupMiddleware",
]

# Templates
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

# Template caching for production
if not DEBUG:
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        ("django.template.loaders.cached.Loader", [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]),
    ]

# Database configuration with proper fallback
class DatabaseConfig:
    """Centralized database configuration with validation and pooling"""
    
    @staticmethod
    def get_management_db():
        """Get optimized management database config"""
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
        
        # Connection pooling optimization
        config.update({
            "CONN_MAX_AGE": 0 if DEBUG else 600,  # 10 min connection reuse
            "CONN_HEALTH_CHECKS": not DEBUG,
            "ATOMIC_REQUESTS": False,  # Don't wrap every request in transaction
            "AUTOCOMMIT": True,
            "OPTIONS": {
                "options": "-c search_path=management,public",
                "sslmode": "disable" if DEBUG else "require",
                "connect_timeout": 10,
                "client_encoding": "UTF8",
                # PostgreSQL connection pool settings
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
            "TIME_ZONE": env("TIME_ZONE"),
        })
        
        # Add connection pool for production
        if not DEBUG:
            config["OPTIONS"].update({
                "pool": True,  # Enable connection pooling
                "pool_size": 10,  # Number of connections to maintain
                "max_overflow": 20,  # Maximum overflow connections
                "pool_recycle": 3600,  # Recycle connections after 1 hour
                "pool_pre_ping": True,  # Verify connections before use
            })
        
        return config
    
    @staticmethod
    def get_study_db_config(db_name: str):
        """Get optimized study database config"""
        return {
            "ENGINE": env("STUDY_DB_ENGINE"),
            "NAME": db_name,
            "USER": env("STUDY_PGUSER"),
            "PASSWORD": env("STUDY_PGPASSWORD"),
            "HOST": env("STUDY_PGHOST"),
            "PORT": env.int("STUDY_PGPORT"),
            "CONN_MAX_AGE": 0 if DEBUG else 300,  # 5 min for study DBs
            "CONN_HEALTH_CHECKS": True,
            "ATOMIC_REQUESTS": False,
            "OPTIONS": {
                "options": f"-c search_path={env('STUDY_DB_SEARCH_PATH')},public",
                "sslmode": "disable" if DEBUG else "require",
                "connect_timeout": 5,
                "statement_timeout": "30000",  # 30 seconds timeout
                "idle_in_transaction_session_timeout": "60000",  # 60 seconds
            },
        }

DATABASES = {
    "default": DatabaseConfig.get_management_db()
}

DATABASES["default"]["OPTIONS"]["options"] = "-c search_path=management,public"

# Database Routers
DATABASE_ROUTERS = ['backend.tenancy.db_router.TenantRouter'] 

# Study Database Settings
STUDY_DB_PREFIX = env("STUDY_DB_PREFIX")
STUDY_DB_ENGINE = env("STUDY_DB_ENGINE")


# Custom User Model
AUTH_USER_MODEL = 'tenancy.User'

# Internationalization
LANGUAGE_CODE = env("DEFAULT_LANGUAGE")
LANGUAGES = [
    ("vi", "Tiếng Việt"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = env("TIME_ZONE")
DATE_FORMAT=env("DATE_FORMAT")
TIME_FORMAT=env("TIME_FORMAT")
DATETIME_FORMAT = env("DATETIME_FORMAT")
USE_TZ = True

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

# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"]  # Updated to match layout (frontend/static instead of apps/web/static)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Static files optimization
if not DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Authentication
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
FEATURE_PASSWORD_RESET = env.bool("FEATURE_PASSWORD_RESET")

# Security Settings (environment-aware)
SESSION_ENGINE = "django.contrib.sessions.backends.cache" if not DEBUG else "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False  # Only save when modified
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_BROWSER_XSS_FILTER = True

# Additional security settings
if not DEBUG:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    CSRF_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_SAMESITE = "Strict"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration (optimized and reduced)
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
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
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
        "backend.studies": {  # Added logger for studies app to match layout
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "axes": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


# --- CACHES and other settings continue below ---
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
            "OPTIONS": {
                "MAX_ENTRIES": 1000,
                "CULL_FREQUENCY": 3,
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
                "IGNORE_EXCEPTIONS": True,  # Don't fail if Redis is down
            },
            "KEY_PREFIX": "ressync",
            "VERSION": 1,
        }
    }

# Cache timeouts
CACHE_MIDDLEWARE_SECONDS = 300 if not DEBUG else 0
CACHE_MIDDLEWARE_KEY_PREFIX = 'ressync'

# Email Configuration
if FEATURE_PASSWORD_RESET:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env.int("EMAIL_PORT")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    
    # Validate email settings in production
    if not DEBUG and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
        raise ValueError("EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required when FEATURE_PASSWORD_RESET is True")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Custom Settings
TENANCY_ENABLED = env.bool("TENANCY_ENABLED")
TENANCY_STUDY_CODE_PREFIX = env("TENANCY_STUDY_CODE_PREFIX")
 
# Thread-local storage
THREAD_LOCAL = threading.local()

# Add AUTHENTICATION_BACKENDS
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",  # Moved AxesBackend first to check lockouts before authentication
    "django.contrib.auth.backends.ModelBackend",
]

# Axes settings (optimized for username-only lockout; removed unused IP-related and whitelist settings)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCK_OUT_AT_FAILURE = True  # Default is True, but kept for clarity
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = ["username"]  # Simplified to lock only by username (removed extra list nesting)
AXES_VERBOSE = False
AXES_CACHE = "default"  # Kept as it uses the default cache; adjust if switching to cache handler

# # Axes email notifications
# SEND_LOCKOUT_EMAIL = env.bool("SEND_LOCKOUT_EMAIL", default=False)
# SECURITY_EMAIL = env("SECURITY_EMAIL", default="security@example.com")
# DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# # Auto-unlock after certain time (optional)
# AXES_LOCKOUT_CALLABLE = None  # Use default or custom as shown earlier

# # Template for lockout page
# AXES_LOCKOUT_TEMPLATE = "axes/lockout.html"

# # Enable logging
# AXES_VERBOSE = True if DEBUG else False

# # Use database for tracking (more reliable than cache)
# AXES_HANDLER = "axes.handlers.database.AxesStandaloneHandler"

# # Clean old attempts periodically
# AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False

# # Additional context for lockout template
# AXES_LOCKOUT_CALLABLE = "backend.management.utils.axes_lockout_response"

# # Support email for lockout page
# SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="support@example.com")

# Password Hashers
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