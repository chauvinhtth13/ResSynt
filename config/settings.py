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

import environ
from pathlib import Path
from django.utils.translation import gettext_lazy as _


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variable management using django-environ.
env = environ.Env(
    DEBUG=(bool, False),
    TENANCY_ENABLED=(bool, True),
    FEATURE_PASSWORD_RESET=(bool, False),
)

# Read .env file
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# ==========================================
# CORE SETTINGS
# ==========================================

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# URLs
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ==========================================
# INSTALLED APPS (OPTIMIZED)
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
    "rest_framework",
    "corsheaders",
    "axes",
    'django_bootstrap5',
    "chartjs",
    "parler",
]

LOCAL_APPS = [
    "backend.tenancy",
    "backend.api",
    "backend.studies",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==========================================
# MIDDLEWARE (SIMPLIFIED)
# ==========================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware", 
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",

    "backend.tenancy.middleware.SecurityHeadersMiddleware",
    "backend.tenancy.middleware.PerformanceMonitoringMiddleware",
    "backend.tenancy.middleware.StudyRoutingMiddleware",
    "backend.tenancy.middleware.CacheControlMiddleware",
    "backend.tenancy.middleware.DatabaseConnectionCleanupMiddleware",
]

# ==========================================
# TEMPLATES
# ==========================================

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
        },
    },
]

# Template caching in production
if not DEBUG:
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        ("django.template.loaders.cached.Loader", [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]),
    ]



# ==========================================
# DATABASE (SIMPLIFIED)
# ==========================================

# Main database
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
            "TIME_ZONE": 'Asia/Ho_Chi_Minh',
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

# Primary database configuration.
DATABASES = {
    "default": DatabaseConfig.get_management_db()
}

# Routers for multi-database (tenancy) setup.
DATABASE_ROUTERS = ['backend.tenancy.db_router.TenantRouter']


# Prefix for study database names and engine.
STUDY_DB_PREFIX = env("STUDY_DB_PREFIX")
STUDY_DB_ENGINE = env("STUDY_DB_ENGINE")
TENANCY_STUDY_CODE_PREFIX = env("TENANCY_STUDY_CODE_PREFIX")

# ==========================================
# AUTHENTICATION
# ==========================================

AUTH_USER_MODEL = "tenancy.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Password hashers (only keep Argon2 and PBKDF2)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# ==========================================
# AXES (BRUTE FORCE PROTECTION)
# ==========================================

AXES_FAILURE_LIMIT = 5  # Reduced from 8
AXES_COOLOFF_TIME = 1  # 1 hour cooloff
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username"]]
AXES_ENABLED = not DEBUG  # Disable in development

# ==========================================
# INTERNATIONALIZATION
# ==========================================

# Enable i18n
USE_I18N = True
USE_L10N = True  # Localization for dates, numbers
USE_TZ = True

# Default language
LANGUAGE_CODE = 'vi'  # Vietnamese as default

# Available languages
LANGUAGES = [
    ('vi', _('Vietnamese')),  # Tiếng Việt
    ('en', _('English')),     # Tiếng Anh
]

LANGUAGE_COOKIE_NAME = 'django_language'
LANGUAGE_COOKIE_AGE = None  # Browser session
LANGUAGE_COOKIE_DOMAIN = None
LANGUAGE_COOKIE_PATH = '/'
LANGUAGE_COOKIE_SECURE = False
LANGUAGE_COOKIE_HTTPONLY = False
LANGUAGE_COOKIE_SAMESITE = 'Lax'

# Locale paths - where translation files are stored
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Time zone
TIME_ZONE = 'Asia/Ho_Chi_Minh'  # Vietnam timezone

# Date and time formats for Vietnamese
DATE_FORMAT = 'd/m/Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd/m/Y H:i:s'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'

# Input formats for forms
DATE_INPUT_FORMATS = [
    '%d/%m/%Y',  # '25/10/2006'
    '%d-%m-%Y',  # '25-10-2006'
    '%Y-%m-%d',  # '2006-10-25'
]

TIME_INPUT_FORMATS = [
    '%H:%M:%S',  # '14:30:59'
    '%H:%M',     # '14:30'
]

DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%d-%m-%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
]

# Number formats
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','
NUMBER_GROUPING = 3

# First day of week (0=Monday, 6=Sunday)
FIRST_DAY_OF_WEEK = 1  # Monday

# Parler settings for multilingual models.
PARLER_DEFAULT_LANGUAGE_CODE = 'en'
PARLER_LANGUAGES = {
    None: tuple({"code": code} for code, _ in LANGUAGES),
    'default': {
        'fallbacks': ['en'],
        'hide_untranslated': False,
    }
}

# ==========================================
# STATIC & MEDIA FILES
# ==========================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"] if (BASE_DIR / "frontend" / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if not DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# ==========================================
# BOOTSTRAP5 SETTINGS
# ==========================================
BOOTSTRAP5 = {
    # CSS: Sử dụng local file để tránh phụ thuộc CDN (tốc độ nhanh hơn, offline ok, nhưng cần collectstatic)
    'css_url': {
        'url': f"{STATIC_URL}css/bootstrap/bootstrap.css",  # Đảm bảo path tồn tại: frontend/static/css/default/bootstrap.min.css
        # Bỏ integrity/crossorigin vì local, nhưng nếu dùng CDN thì thêm để security
    },

    # The complete URL to the Bootstrap bundle JavaScript file.
    "javascript_url": {
        'url': f"{STATIC_URL}js/bootstrap/bootstrap.bundle.min.js",
    },

    'required_css_class': 'required',
    'error_css_class': 'is-invalid',
    'success_css_class': 'is-valid',

    'wrapper_class': 'mb-3',

    'inline_wrapper_class': '',

    'horizontal_label_class': 'col-sm-2',

    'horizontal_field_class': 'col-sm-10',

    'horizontal_field_offset_class': 'offset-sm-2',

    'set_placeholder': True,

    'server_side_validation': True,

    'formset_renderers':{
        'default': 'django_bootstrap5.renderers.FormsetRenderer',
    },
    'form_renderers': {
        'default': 'django_bootstrap5.renderers.FormRenderer',
    },
    'field_renderers': {
        'default': 'django_bootstrap5.renderers.FieldRenderer',
    },
}

# ==========================================
# SECURITY
# ==========================================

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"  # Better than cache-only
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax" if DEBUG else "Strict"

# CSRF settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax" if DEBUG else "Strict"

# Security headers
SECURE_SSL_REDIRECT = not DEBUG
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# HSTS (only in production)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ==========================================
# CACHING (SIMPLIFIED)
# ==========================================

if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
else:
    # Use Redis in production if available
    redis_url = env("REDIS_URL")
    if redis_url:
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": redis_url,
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "IGNORE_EXCEPTIONS": True,  # Fallback if Redis fails
                }
            }
        }
    else:
        # Fallback to database cache
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.db.DatabaseCache",
                "LOCATION": "cache_table",
            }
        }

# ==========================================
# LOGGING (SIMPLIFIED)
# ==========================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
        },
    },
    "root": {
        "handlers": ["console"] if DEBUG else ["console", "file"],
        "level": "INFO" if DEBUG else "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"] if DEBUG else ["console", "file"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
    },
}

# ==========================================
# EMAIL (ONLY IF NEEDED)
# ==========================================

if env("FEATURE_PASSWORD_RESET"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env.int("EMAIL_PORT")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ==========================================
# REST FRAMEWORK
# ==========================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ] if not DEBUG else [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ==========================================
# CORS CONFIGURATION
# ==========================================

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

CORS_ALLOW_CREDENTIALS = True

# Authentication Redirects
# ------------------------
# URLs for login, logout, and redirects.
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/select-study/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# ==========================================
# OTHER SETTINGS
# ==========================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"