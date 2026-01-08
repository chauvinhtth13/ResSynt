"""
Logging configuration.

Log levels:
- Console: ERROR only (minimal noise)
- all.log: DEBUG in dev, INFO in prod (comprehensive)
- error.log: ERROR+ (critical issues)
- security.log: WARNING+ (security events)
- audit.log: INFO (compliance trail)
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

_DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # -------------------------------------------------------------------------
    # FORMATTERS
    # -------------------------------------------------------------------------
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
    },
    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    # -------------------------------------------------------------------------
    # HANDLERS
    # -------------------------------------------------------------------------
    "handlers": {
        # Console - errors only
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "minimal",
            "level": "ERROR",
        }, 
        # Console for dev - more verbose
        "console_dev": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
            "filters": ["require_debug_true"],
        },
        # All logs
        "file_all": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "all.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "DEBUG" if _DEBUG else "INFO",
            "encoding": "utf-8",
        },
        # Error logs
        "file_error": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "error.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 10,
            "formatter": "verbose",
            "level": "ERROR",
            "encoding": "utf-8",
        },
        # Security logs
        "file_security": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "security.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 20,
            "formatter": "verbose",
            "level": "WARNING",
            "encoding": "utf-8",
        },
        # Audit trail
        "file_audit": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "audit.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 30,  # Keep longer for compliance
            "formatter": "verbose",
            "level": "INFO",
            "encoding": "utf-8",
        },
        # Database queries (dev only)
        "file_db": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOGS_DIR / "database.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
            "level": "DEBUG" if _DEBUG else "WARNING",
            "encoding": "utf-8",
        },
    },
    # -------------------------------------------------------------------------
    # ROOT LOGGER
    # -------------------------------------------------------------------------
    "root": {
        "handlers": ["console", "file_all", "file_error"],
        "level": "DEBUG" if _DEBUG else "INFO",
    },
    # -------------------------------------------------------------------------
    # MODULE LOGGERS
    # -------------------------------------------------------------------------
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
            "level": "DEBUG" if _DEBUG else "WARNING",
            "propagate": False,
        },
        # Application
        "backends.tenancy": {
            "handlers": [],
            "level": "DEBUG" if _DEBUG else "INFO",
            "propagate": True,
        },
        "backends.studies": {
            "handlers": [],
            "level": "DEBUG" if _DEBUG else "INFO",
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
            "level": "DEBUG" if _DEBUG else "WARNING",
            "propagate": False,
        },
        # Audit logger (use: logging.getLogger('audit').info(...))
        "audit": {
            "handlers": ["file_audit"],
            "level": "INFO",
            "propagate": False,
        },
        # Third-party (reduce noise)
        "axes": {
            "handlers": ["file_security"],
            "level": "WARNING",  # Suppress INFO startup messages
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
# =============================================================================
    