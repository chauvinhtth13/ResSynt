# backends/api/base/account/__init__.py
"""
Custom account module for allauth + axes integration.
Provides enhanced security with inline lockout handling.

Usage:
    from backends.api.base.account.forms import AxesLoginForm
    from backends.api.base.account.views import SecureLoginView
    from backends.api.base.account.lockout import lockout_response

Note: We use lazy imports to avoid circular import issues with axes checks.
"""

# Lazy imports - don't import at module level to avoid circular imports
# when axes validates AXES_LOCKOUT_CALLABLE during startup

__all__ = [
    'AxesLoginForm',
    'SecureLoginView', 
    'lockout_response',
]


def __getattr__(name):
    """Lazy import to avoid circular imports during axes startup checks."""
    if name == 'AxesLoginForm':
        from .forms import AxesLoginForm
        return AxesLoginForm
    elif name == 'SecureLoginView':
        from .views import SecureLoginView
        return SecureLoginView
    elif name == 'lockout_response':
        from .lockout import lockout_response
        return lockout_response
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
