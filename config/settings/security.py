"""
Security settings - CSP, headers, password validators, CSRF.

These are base security settings shared across all environments.
Environment-specific overrides (HTTPS, cookies) are in dev.py and prod.py.
"""
import environ

env = environ.Env()

# =============================================================================
# CSRF PROTECTION
# =============================================================================

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_USE_SESSIONS = True
CSRF_COOKIE_AGE = None
# Note: CSRF_COOKIE_SECURE is set in dev.py (False) and prod.py (True)

# =============================================================================
# SECURITY HEADERS
# =============================================================================

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Note: HTTPS settings (SSL_REDIRECT, HSTS) are configured in prod.py only

# =============================================================================
# PERMISSIONS POLICY
# =============================================================================

PERMISSIONS_POLICY = {
    "accelerometer": [],
    "camera": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "payment": [],
    "usb": [],
}

# =============================================================================
# CONTENT SECURITY POLICY (django-csp 4.0)
# =============================================================================

try:
    from csp.constants import SELF
except ImportError:
    SELF = "'self'"

CSP_ENABLED = True

# Base CSP directives - shared across environments
_CSP_BASE_DIRECTIVES = {
    "default-src": [SELF],
    "script-src": [
        SELF,
        "https://cdn.jsdelivr.net",
        "https://ajax.googleapis.com",
    ],
    "style-src": [
        SELF,
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
        "blob:",
        # Specific trusted domains for images
        "https://cdn.jsdelivr.net",
        "https://www.gravatar.com",
        "https://ui-avatars.com",
    ],
    "connect-src": [SELF],
    "frame-ancestors": ["'none'"],
    "base-uri": [SELF],
    "form-action": [SELF],
}

# Copy directives to avoid mutation issues
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {k: list(v) for k, v in _CSP_BASE_DIRECTIVES.items()},
}

CSP_INCLUDE_NONCE_IN = ["script-src", "style-src"]

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {
            "user_attributes": ("username", "first_name", "last_name", "email"),
            "max_similarity": 0.7,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# PASSWORD HASHERS (ordered by preference)
# =============================================================================

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
