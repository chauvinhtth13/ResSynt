"""
Logging configuration.

This module is imported by base.py before DEBUG is set.
Uses DJANGO_ENV to determine environment-specific logging levels.

Log levels by environment:
- Development:
  - Console: DEBUG (verbose output)
  - all.log: DEBUG (comprehensive)
- Production:
  - Console: ERROR only (minimal noise)
  - all.log: INFO (standard logging)
  - JSON format for centralized logging (ELK/Loki compatible)

Log files:
- all.log: All application logs
- error.log: ERROR+ only (critical issues)
- security.log: WARNING+ (security events from axes, django.security)
- audit.log: INFO (compliance trail)
- database.log: Query logging (DEBUG in dev, WARNING in prod)
"""
import os
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Determine environment from DJANGO_ENV (same as __init__.py uses)
_DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev").lower()
_IS_DEV = _DJANGO_ENV in ("dev", "development", "test")
_IS_PROD = _DJANGO_ENV in ("prod", "production")

# Log levels based on environment
_ALL_LOG_LEVEL = "DEBUG" if _IS_DEV else "INFO"
_DB_LOG_LEVEL = "DEBUG" if _IS_DEV else "WARNING"
_ROOT_LOG_LEVEL = "DEBUG" if _IS_DEV else "INFO"

# Use JSON logging in production for centralized logging systems
_USE_JSON_LOGGING = os.environ.get("LOG_FORMAT", "text").lower() == "json" or _IS_PROD

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # =========================================================================
    # FORMATTERS
    # =========================================================================
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} | {name} | {module}.{funcName}:{lineno} | {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{levelname}] {asctime} | {message}",
            "style": "{",
            "datefmt": "%H:%M:%S",
        },
        "minimal": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
        # JSON format for centralized logging (ELK/Loki/CloudWatch)
        "json": {
            "()": "django.utils.log.ServerFormatter" if _IS_DEV else "logging.Formatter",
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
    },
    # =========================================================================
    # FILTERS
    # =========================================================================
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    # =========================================================================
    # HANDLERS
    # =========================================================================
    "handlers": {
        # Console - errors only (production default)
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if _USE_JSON_LOGGING else "minimal",
            "level": "ERROR",
        },
        # Console for development - verbose output (only active when DEBUG=True)
        "console_dev": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
            "filters": ["require_debug_true"],
        },
        # Console JSON for production (stdout for container/cloud logging)
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO",
        },
        # All logs (comprehensive)
        "file_all": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "all.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "formatter": "json" if _USE_JSON_LOGGING else "verbose",
            "level": _ALL_LOG_LEVEL,
            "encoding": "utf-8",
        },
        # Error logs only
        "file_error": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "error.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "ERROR",
            "encoding": "utf-8",
        },
        # Security logs (axes, django.security)
        "file_security": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "security.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 20,
            "formatter": "verbose",
            "level": "WARNING",
            "encoding": "utf-8",
        },
        # Audit trail (compliance)
        "file_audit": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "audit.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 30,  # Longer retention for compliance
            "formatter": "verbose",
            "level": "INFO",
            "encoding": "utf-8",
        },
        # Database queries
        "file_db": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "database.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
            "level": _DB_LOG_LEVEL,
            "encoding": "utf-8",
        },
    },
    # =========================================================================
    # ROOT LOGGER
    # =========================================================================
    "root": {
        "handlers": ["console", "file_all", "file_error"],
        "level": _ROOT_LOG_LEVEL,
    },
    # =========================================================================
    # MODULE LOGGERS
    # =========================================================================
    "loggers": {
        # Django core
        "django": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["file_error"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["file_security"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["file_db"],
            "level": _DB_LOG_LEVEL,
            "propagate": False,
        },
        # Application loggers
        "backends.tenancy": {
            "handlers": [],
            "level": _ROOT_LOG_LEVEL,
            "propagate": True,
        },
        "backends.studies": {
            "handlers": [],
            "level": _ROOT_LOG_LEVEL,
            "propagate": True,
        },
        "backends.studies.study_loader": {
            "handlers": ["file_all"],
            "level": "DEBUG",
            "propagate": False,
        },
        # API account (auth, lockout, etc.)
        "backends.api.base.account": {
            "handlers": ["console_dev", "file_security"],
            "level": "DEBUG" if _IS_DEV else "WARNING",
            "propagate": False,
        },
        # Audit logger (usage: logging.getLogger('audit').info(...))
        "audit": {
            "handlers": ["file_audit"],
            "level": "INFO",
            "propagate": False,
        },
        # Third-party (reduce noise)
        "axes": {
            "handlers": ["file_security"],
            "level": "WARNING",
            "propagate": False,
        },
        "environ": {
            "handlers": [],
            "level": "WARNING",
            "propagate": True,
        },
        "PIL": {
            "handlers": [],
            "level": "WARNING",
            "propagate": True,
        },
        "celery": {
            "handlers": [],
            "level": "WARNING",
            "propagate": True,
        },
    },
}