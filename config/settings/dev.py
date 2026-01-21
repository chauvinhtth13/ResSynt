"""
Development settings.

Usage: DJANGO_ENV=dev python manage.py runserver

Features:
- DEBUG=True for detailed error pages
- Local memory cache (no Redis dependency)
- Console email backend
- Relaxed security (no HTTPS)
- Verbose logging and Axes debugging
- Optional debug toolbar support
"""
from .base import *  # noqa: F401, F403

# =============================================================================
# CORE SETTINGS
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".localhost"]

# =============================================================================
# DATABASE (Development optimizations)
# =============================================================================

# Add statement timeout for dev consistency with prod
DATABASES["default"]["OPTIONS"] = DATABASES["default"].get("OPTIONS", {})  # noqa: F405
DATABASES["default"]["OPTIONS"]["options"] = "-c statement_timeout=60000"  # 60s for dev (longer than prod)  # noqa: F405

# =============================================================================
# SECURITY (Relaxed for development)
# =============================================================================

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False

# CSP: Allow unsafe-inline for development convenience
CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"].append("'unsafe-inline'")  # noqa: F405
CONTENT_SECURITY_POLICY["DIRECTIVES"]["style-src"].append("'unsafe-inline'")  # noqa: F405

# CSP report-only mode (logs violations but doesn't block)
CONTENT_SECURITY_POLICY_REPORT_ONLY = {
    "DIRECTIVES": {k: list(v) for k, v in CONTENT_SECURITY_POLICY["DIRECTIVES"].items()},  # noqa: F405
}

# =============================================================================
# CACHE
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "resync-dev-cache",
        "OPTIONS": {"MAX_ENTRIES": 1000},
    }
}

# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# AXES (Verbose for debugging)
# =============================================================================

AXES_VERBOSE = True
AXES_LOCKOUT_CALLABLE = "backends.api.base.account.lockout.dev_lockout_response"
AXES_IPWARE_PROXY_COUNT = 0
AXES_IPWARE_META_PRECEDENCE_ORDER = ["REMOTE_ADDR"]

# =============================================================================
# LOGGING
# =============================================================================

LOGGING["root"]["handlers"].append("console_dev")  # noqa: F405

# =============================================================================
# DEBUG TOOLBAR (optional)
# =============================================================================

try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(  # noqa: F405
        MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1,  # noqa: F405
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )
    INTERNAL_IPS = ["127.0.0.1", "::1"]
except ImportError:
    pass