# config/settings.py (FINAL OPTIMIZED VERSION - CLEANED)
"""
Optimized Django settings for ResSync Database-per-Study Platform
With proper schema configuration for study databases
"""
import os
import environ
import sys
from pathlib import Path
from django.utils.translation import gettext_lazy as _
import logging
from config.utils import load_study_apps, DatabaseConfig

if sys.platform == 'win32':
    # Set environment variable for UTF-8 encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Setup logging early
logging.basicConfig(level=logging.WARNING)  # Chỉ hiện WARNING trở lên
logger = logging.getLogger(__name__)

# ==========================================
# BASE CONFIGURATION
# ==========================================

# Environment setup
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, None),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)

# Read .env file
env_file = BASE_DIR / ".env"
if os.path.exists(env_file):
    environ.Env.read_env(env_file)
else:
    print(f"Warning: {env_file} not found. Using environment variables.")

# ---------- Core Settings ----------
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set and at least 50 characters long")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

# Allowed hosts for the application
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production")

AUTH_USER_MODEL = 'tenancy.User' 


# ---------- URL Configuration ----------
ROOT_URLCONF = "config.urls"

# ---------- WSGI Configuration ----------
WSGI_APPLICATION = "config.wsgi.application"

# ---------- CSRF Protection ----------
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")


# ==========================================
# STUDY DATABASE CONFIGURATION
# ==========================================

STUDY_DB_PREFIX = env("STUDY_DB_PREFIX", default="db_study_")
STUDY_DB_SCHEMA = env("STUDY_DB_SCHEMA", default="data")
MANAGEMENT_DB_SCHEMA = env("MANAGEMENT_DB_SCHEMA", default="management")


# ==========================================
# INSTALLED APPS
# ==========================================

# Site configuration
SITE_ID = 1

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.sites',
    'django.contrib.humanize',
]


THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    'allauth.usersessions',
    "axes",
    "csp",
    "parler",
    "django_extensions",
    'encrypted_model_fields',
]

BASE_LOCAL_APPS = [
    "backends.tenancy",
    "backends.api",
    "backends.studies",
    
]

# ==========================================
# LOAD STUDY APPS SAFELY
# ==========================================

STUDY_DB_PREFIX = env("STUDY_DB_PREFIX")
STUDY_DB_SCHEMA = env("STUDY_DB_SCHEMA")

STUDY_APPS, HAS_STUDY_ERRORS = load_study_apps()

# Combine all apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + BASE_LOCAL_APPS + STUDY_APPS

if DEBUG:
    logger.debug(f"Study apps loaded: {STUDY_APPS}")
    if HAS_STUDY_ERRORS:
        logger.warning("Some study apps failed to load. Check previous logs for details.")
    logger.debug(f"Installed apps count: {len(INSTALLED_APPS)}")
    logger.debug(f"List installed: {INSTALLED_APPS}")



# ==========================================
# MIDDLEWARE (OPTIMIZED ORDER)
# ==========================================
MIDDLEWARE = [
    # Security & Performance
    "django.middleware.security.SecurityMiddleware",
    
    # WhiteNoise (sau SecurityMiddleware để static files được bảo vệ)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    
    # Session (cần cho authentication và messages)
    "django.contrib.sessions.middleware.SessionMiddleware",
    
    # Common operations
    "django.middleware.common.CommonMiddleware",
    
    # CSRF Protection
    "django.middleware.csrf.CsrfViewMiddleware",
    
    # Authentication
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    
    # Messages (sau auth)
    "django.contrib.messages.middleware.MessageMiddleware",
    
    # Locale (sau messages, trước clickjacking)
    "django.middleware.locale.LocaleMiddleware",
    
    # Clickjacking
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # Security & Rate Limiting
    "axes.middleware.AxesMiddleware",

    'backends.tenancy.middleware.UnifiedTenancyMiddleware',

    # Allauth
    "allauth.account.middleware.AccountMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
    # Block signup
    'backends.tenancy.middleware.BlockSignupMiddleware',

    # Content Security Policy
    "csp.middleware.CSPMiddleware",

]



# ==========================================
# INITIALIZE DATABASES
# ==========================================

try:
    from psycopg_pool import ConnectionPool
    HAS_PSYCOPG_POOL = True
except ImportError:
    HAS_PSYCOPG_POOL = False
    logger.warning("psycopg_pool not installed. Install with: pip install psycopg[pool]")

# Start with management database only
DATABASES = {
    "default": DatabaseConfig.get_management_db(env),
}

# Validate
DatabaseConfig.validate_config(DATABASES["default"], "default")

if not DEBUG:
    # Production optimizations
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    
    # If using pgbouncer
    if env.bool("USE_PGBOUNCER"):
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

try:
    from backends.studies.study_loader import get_study_databases

    study_databases = get_study_databases()

    if study_databases:
        DATABASES.update(study_databases)
except Exception as e:
    logger.error(f"Error configuring databases: {e}")

# Database router
DATABASE_ROUTERS = ["backends.tenancy.db_router.TenantRouter"]

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
                'backends.studies.study_43en.services.context_processors.upcoming_appointments',
                "django.template.context_processors.media",
                'backends.studies.study_43en.services.context_processors.study_context',
                "django.template.context_processors.tz",
            ],
        },
    },
]

# Use cached template loader in production for better performance
if not DEBUG:
    TEMPLATES[0]["APP_DIRS"] = False
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        ("django.template.loaders.cached.Loader", [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]),
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
    redis_url = env("REDIS_URL", default=None)
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
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = 'resync'

# ==========================================
# SESSION CONFIGURATION
# ==========================================

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 28800  # 8pi hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = False

# ==========================================
# AUTHENTICATION & AXES
# ==========================================

AUTHENTICATION_BACKENDS = [
    # Django default backend (first priority)
    "django.contrib.auth.backends.ModelBackend",
    
    # Allauth authentication
    "allauth.account.auth_backends.AuthenticationBackend",
    
    # Axes MUST be last to intercept login failures
    "axes.backends.AxesBackend",
]

# Allauth settings
ANONYMOUS_USER_NAME = None

# ==========================================
# DJANGO-ALLAUTH CONFIGURATION
# ==========================================

# ---------- Account Adapter ----------
# Note: You have this defined twice - using the custom one
# ACCOUNT_ADAPTER = "allauth.account.adapter.DefaultAccountAdapter"  # Remove this duplicate
ACCOUNT_ADAPTER = "backends.api.base.account.adapter.CustomAccountAdapter"

# ---------- Registration Settings ----------
ACCOUNT_ALLOW_REGISTRATION = False
SOCIALACCOUNT_ALLOW_REGISTRATION = False

# ---------- Authentication Methods ----------
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SESSION_REMEMBER = False

# ---------- Username Configuration ----------
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_BLACKLIST = ["admin", "administrator", "root", "system"]

# ---------- Email Settings ----------
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[ResSync - Research Data Management Platform]"
ACCOUNT_EMAIL_NOTIFICATIONS = True

# ---------- Password Settings ----------
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
PASSWORD_RESET_TIMEOUT = 900  # 15 minutes

# ---------- Rate Limiting ----------
ACCOUNT_RATE_LIMITS = {
    # Password operations
    "change_password": "5/m/user",         # 5 attempts per minute per user
    "reset_password": "10/m/ip",           # 10 attempts per minute per IP
    "reset_password_email": "5/m/ip",      # 5 emails per minute per IP
    "reset_password_from_key": "20/m/ip",  # 20 attempts per minute per IP
    
    # Login operations
    "login": "20/m/ip",                    # 20 login attempts per minute per IP
    "login_failure": "10/m/ip",            # 10 failed login attempts per minute per IP
}

# ---------- Authentication URLs ----------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Allauth logout behavior
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"
# 🔒 SECURITY FIX: Disabled GET logout to prevent CSRF attacks
ACCOUNT_LOGOUT_ON_GET = False  # Require POST request for logout (prevent CSRF)

USERSESSIONS_TRACK_ACTIVITY = True


# ==========================================
# AXES CONFIGURATION (BRUTE-FORCE PROTECTION)
# ==========================================
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 7
AXES_COOLOFF_TIME = None
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_AT_FAILURE = True # Manual check mode
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_VERBOSE = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_LOCKOUT_TEMPLATE="errors/lockout.html"


# ==========================================
# RATE LIMITING CONFIGURATION
# ==========================================

RATELIMIT_ENABLE = env.bool('RATELIMIT_ENABLE')
RATELIMIT_USE_CACHE = 'default'

# ==========================================
# EMAIL CONFIGURATION
# ==========================================
EMAIL_BACKEND =  env("EMAIL_BACKEND")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = env("SERVER_EMAIL")


# ==========================================
# CSP CONFIGURATION (django-csp 4.0)
# ==========================================

try:
    from csp.constants import SELF
except ImportError:
    SELF = "'self'"

# Enable CSP
CSP_ENABLED = True

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [
            SELF,
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://ajax.googleapis.com",
        ],
        "style-src": [
            SELF,
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
            "https://cdn.jsdelivr.net",
        ],
        "font-src": [
            SELF,
            "https://fonts.gstatic.com",
            "data:",
        ],
        "img-src": [
            SELF,
            "data:",
            "https:",
        ],
        "connect-src": [SELF],
        "frame-ancestors": ["'none'"],
        "base-uri": [SELF],
        "form-action": [SELF],
    },
}

CSP_INCLUDE_NONCE_IN = ['script-src', 'style-src']

# Report-only mode trong development
if DEBUG:
    # Tạo policy report-only để test không ảnh hưởng trang
    CONTENT_SECURITY_POLICY_REPORT_ONLY = CONTENT_SECURITY_POLICY.copy()


# ==========================================
# CELERY CONFIGURATION
# ==========================================
if DEBUG:
    # Development: Eager mode (synchronous, no broker needed)
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    # Production: Redis broker
    CELERY_BROKER_URL = env("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")

    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_TIMEZONE = "Asia/Ho_Chi_Minh"

    # Task settings
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
    CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

    # Worker settings
    CELERY_WORKER_PREFETCH_MULTIPLIER = 4
    CELERY_WORKER_MAX_TASKS_PER_CHILD = 100


# ==========================================
# INTERNATIONALIZATION
# ==========================================
USE_I18N = True
USE_TZ = True

# Default language - Vietnamese
LANGUAGE_CODE = 'vi'

# Available languages
LANGUAGES = [
    ('vi', _('Tiếng Việt')),  # Vietnamese first
    ('en', _('English')),      # English second
]

# Language cookie settings
LANGUAGE_COOKIE_NAME = 'django_language'
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60  # 1 year
LANGUAGE_COOKIE_DOMAIN = None
LANGUAGE_COOKIE_PATH = '/'
LANGUAGE_COOKIE_SECURE = not DEBUG  # Automatically secure in production
LANGUAGE_COOKIE_HTTPONLY = False
LANGUAGE_COOKIE_SAMESITE = 'Lax'

# Language session key
LANGUAGE_SESSION_KEY = '_language'

# Locale paths - where translation files are stored
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Time zone - Vietnam
TIME_ZONE = 'Asia/Ho_Chi_Minh'

# Vietnamese date/time formats
DATE_FORMAT = 'd/m/Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd/m/Y H:i:s'
YEAR_MONTH_FORMAT = 'm/Y'
MONTH_DAY_FORMAT = 'd/m'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'

# Input formats for forms (Vietnamese style)
DATE_INPUT_FORMATS = [
    '%d/%m/%Y',  # '25/09/2025'
    '%d-%m-%Y',  # '25-09-2025'
    '%d.%m.%Y',  # '25.09.2025'
    '%Y-%m-%d',  # '2025-09-25' (ISO)
]

TIME_INPUT_FORMATS = [
    '%H:%M:%S',  # '14:30:59'
    '%H:%M',     # '14:30'
    '%H-%M-%S',  # '14-30-59'
    '%H-%M',     # '14-30'
]

DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%d-%m-%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',
    '%d.%m.%Y %H:%M:%S',
    '%d.%m.%Y %H:%M',
    '%Y-%m-%d %H:%M:%S',  # ISO
    '%Y-%m-%d %H:%M',
]

# Number formats (Vietnamese style)
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','
NUMBER_GROUPING = 3

# First day of week (Monday)
FIRST_DAY_OF_WEEK = 1

# Parler configuration for multi-language models
PARLER_DEFAULT_LANGUAGE_CODE = 'vi'
PARLER_LANGUAGES = {
    None: (
        {'code': 'vi'},  # Vietnamese first
        {'code': 'en'},
    ),
    'default': {
        'fallbacks': ['vi', 'en'],  # Fallback to Vietnamese first
        'hide_untranslated': False,
    }
}

# ==========================================
# STATIC & MEDIA FILES
# ==========================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontends" / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Use manifest static files storage in production
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG
                    else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


# ==========================================
# SECURITY SETTINGS
# ==========================================

# ---------- Security Headers ----------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True  # Deprecated nhưng vẫn hữu ích cho các trình duyệt cũ
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------- Session Configuration ----------
SESSION_COOKIE_NAME = env('SESSION_COOKIE_NAME')
SESSION_COOKIE_AGE = env.int('SESSION_COOKIE_AGE')  # 4 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # Renew session on activity
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Thêm để bảo vệ khỏi XSS

# ---------- CSRF Configuration ----------
CSRF_COOKIE_SECURE = not DEBUG  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True  
CSRF_COOKIE_SAMESITE = "Strict"  # Hoặc "Lax" nếu cần SSO cross-site
CSRF_USE_SESSIONS = True  # Lưu CSRF token trong session
CSRF_COOKIE_AGE = None  # Session cookie

# ---------- HTTPS Settings (Production only) ----------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ==========================================
# LOGGING CONFIGURATION
# ==========================================

# Ensure logs directory exists
# Ensure logs directory exists
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    
    # ---------- Formatters ----------
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
    
    # ---------- Filters ----------
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    
    # ---------- Handlers ----------
    "handlers": {
        # Console output - minimal logging
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console_minimal",
            "level": "ERROR",  # Only ERROR + CRITICAL
        },
        
        #  FIXED: All logs - comprehensive file
        "file_all": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",  #  CHANGED
            "filename": str(LOGS_DIR / "all.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "DEBUG",
            "encoding": "utf-8",
        },
        
        #  FIXED: Error logs - ERROR and above
        "file_error": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",  #  CHANGED
            "filename": str(LOGS_DIR / "error.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "ERROR",
            "encoding": "utf-8",
        },
        
        #  FIXED: Database queries
        "file_db": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",  #  CHANGED
            "filename": str(LOGS_DIR / "database.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 3,
            "formatter": "verbose",
            "level": "DEBUG" if DEBUG else "INFO",
            "encoding": "utf-8",
        },
        
        #  FIXED: Security events
        "file_security": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",  #  CHANGED
            "filename": str(LOGS_DIR / "security.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "WARNING",
            "encoding": "utf-8",
        },
    },
    
    # ---------- Root Logger ----------
    "root": {
        "handlers": ["console", "file_all", "file_error"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
    
    # ---------- Module Loggers ----------
    "loggers": {
        # Django Framework
        "django": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["file_db"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file_error"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security": {
            "handlers": ["file_security"],
            "level": "WARNING",
            "propagate": True,
        },
        
        # Application Modules
        "backends.tenancy": {
            "handlers": [],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
        "backends.studies": {
            "handlers": [],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
        "config.settings": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        
        # Third-party Packages
        "environ": {
            "handlers": [],
            "level": "WARNING",
            "propagate": True,
        },
        "backends.studies.study_loader": {
            "handlers": ["file_all"],
            "level": "DEBUG",
            "propagate": False,
        },
        
        "config.utils": {
            "handlers": ["file_all"],
            "level": "DEBUG",
            "propagate": False,
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
ORGANIZATION_NAME = env("ORGANIZATION_NAME",
                        default="ResSync Research Platform")
PLATFORM_VERSION = env("PLATFORM_VERSION", default="1.0.0")

# ==========================================
# BACKUP CONFIGURATION
# ==========================================

# Backup retention (days)
BACKUP_RETENTION_DAYS = 90  # Keep backups for 90 days

# Backup directory is created in BackupManager.__init__()
# Default: BASE_DIR / 'backups'


# ==========================================
# ADMIN NOTIFICATION CONFIGURATION
# ==========================================

# Admin emails (TO addresses - receive security alerts)
ADMINS = [
    ('Security Team', env('ADMIN_EMAIL', default='admin@resync.local')),
]

# Server name (for email identification)
SERVER_NAME = env('SERVER_NAME', default='ReSYNC Production')


# ==========================================
# PASSWORD VALIDATION
# ==========================================

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

PASSWORD_HASHERS = [
    # Argon2: hiện là thuật toán mạnh nhất, kháng GPU/ASIC tốt, dùng bộ nhớ nhiều
    "django.contrib.auth.hashers.Argon2PasswordHasher",

    # Scrypt: cũng kháng GPU tốt, tương đương Argon2 nhưng chậm hơn và tốn RAM hơn
    "django.contrib.auth.hashers.ScryptPasswordHasher",

    # BCryptSHA256: bảo mật tốt, hỗ trợ rộng rãi, dễ điều chỉnh cost factor
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",

    # 4PBKDF2: mặc định của Django, an toàn và ổn định, nhưng kháng GPU kém hơn
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",

    # 5️PBKDF2-SHA1: bản cũ, giữ lại để tương thích mật khẩu cũ
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]


# ============================================
# ENCRYPTION CONFIGURATION
# ============================================

# Field-level encryption (existing)
FIELD_ENCRYPTION_KEY = env(
    'FIELD_ENCRYPTION_KEY',
    default=''
)

# ✨ NEW: RSA + AES Hybrid Backup Encryption
# RSA Key Configuration
RSA_KEY_SIZE = env.int('RSA_KEY_SIZE', default=4096)
RSA_SIGNATURE_ALGORITHM = 'RSA-PSS'  # Digital signature algorithm
RSA_ENCRYPTION_PADDING = 'OAEP'  # Session key encryption padding

# AES Configuration (for backup data)
AES_KEY_SIZE = 256
AES_MODE = 'GCM'  # Authenticated encryption

# Backup Encryption Method
BACKUP_ENCRYPTION_METHOD = env(
    'BACKUP_ENCRYPTION_METHOD',
    default='HYBRID'  # 'HYBRID' (RSA+AES) or 'SYMMETRIC' (AES only - deprecated)
)

# Signature Verification
BACKUP_SIGNATURE_REQUIRED = env.bool('BACKUP_SIGNATURE_REQUIRED', default=True)

# Server RSA Key Password
SERVER_KEY_PASSWORD = env('SERVER_KEY_PASSWORD', default=None)

# Legacy symmetric encryption password (deprecated, kept for backward compatibility)
BACKUP_ENCRYPTION_PASSWORD = env('BACKUP_ENCRYPTION_PASSWORD', default=None)

# Key Storage
SERVER_KEYS_DIR = BASE_DIR / 'keys' / 'server'
USER_KEYS_DIR = BASE_DIR / 'keys' / 'users'

# Ensure directories exist
SERVER_KEYS_DIR.mkdir(parents=True, exist_ok=True)
USER_KEYS_DIR.mkdir(parents=True, exist_ok=True)

