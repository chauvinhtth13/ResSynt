"""
Development settings.

Usage: DJANGO_ENV=dev python manage.py runserver
"""
from .base import *

DEBUG = True

# =============================================================================
# DEVELOPMENT OVERRIDES
# =============================================================================

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".localhost", "192.168.38.9"]

# =============================================================================
# CACHE (Force LocMemCache in dev - SKIP Redis for speed)
# =============================================================================
# Override base.py cache config to avoid Redis connection delays
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "resync-dev-cache",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        }
    }
}

# Database uses PostgreSQL (same as prod for consistency)

# Disable HTTPS requirements
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
LANGUAGE_COOKIE_SECURE = False

# CSP report-only mode (doesn't block, just logs)
CONTENT_SECURITY_POLICY_REPORT_ONLY = CONTENT_SECURITY_POLICY.copy()

# Allow unsafe-inline for easier development
CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"].append("'unsafe-inline'")
CONTENT_SECURITY_POLICY["DIRECTIVES"]["style-src"].append("'unsafe-inline'")

# =============================================================================
# DEBUG TOOLBAR (optional)
# =============================================================================

try:
    import debug_toolbar
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1,
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )
    INTERNAL_IPS = ["127.0.0.1", "::1"]
except ImportError:
    pass

# =============================================================================
# EMAIL (console output in dev)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# AXES (Development - enable verbose logging)
# =============================================================================

AXES_VERBOSE = True  # Enable verbose logging for debugging

# Bypass lockout for superusers in dev (still tracks attempts)
AXES_LOCKOUT_CALLABLE = "backends.api.base.account.lockout.dev_lockout_response"

# Fix IP detection for localhost (axes shows "None" without this)
AXES_IPWARE_PROXY_COUNT = 0
AXES_IPWARE_META_PRECEDENCE_ORDER = ["REMOTE_ADDR"]


# =============================================================================
# LOGGING
# =============================================================================

# Add console_dev handler for more verbose output
LOGGING["root"]["handlers"].append("console_dev")