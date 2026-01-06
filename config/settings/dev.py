"""
Development settings.

Usage: DJANGO_ENV=dev python manage.py runserver
"""
from .base import *

DEBUG = True

# =============================================================================
# DEVELOPMENT OVERRIDES
# =============================================================================

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".localhost"]

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
# AXES (Disable in development for easier testing)
# =============================================================================

# Option 1: Completely disable AXES in dev
# AXES_ENABLED = False

# Option 2: Keep AXES but whitelist localhost (recommended for testing lockout UI)
AXES_NEVER_LOCKOUT_WHITELIST = True
AXES_IP_WHITELIST = ["127.0.0.1", "::1", "localhost"]


# =============================================================================
# LOGGING
# =============================================================================

# Add console_dev handler for more verbose output
LOGGING["root"]["handlers"].append("console_dev")