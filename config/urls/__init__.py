"""
URL Configuration for Django project.

This module assembles all URL patterns:
- Base URLs (admin, auth, i18n)
- Study-specific APIs (dynamically registered)
- Static/media files (development only)
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from .base import urlpatterns as base_urlpatterns
from .studies import get_study_urlpatterns


# =============================================================================
# Assemble URL Patterns
# =============================================================================

# Start with base patterns
urlpatterns = list(base_urlpatterns)

# Add study-specific APIs
urlpatterns.extend(get_study_urlpatterns())

# Development: serve static and media files
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# =============================================================================
# URL Utilities (for management commands)
# =============================================================================

def get_registered_studies() -> list:
    """
    Get list of registered study codes.
    
    Useful for debugging and management commands.
    
    Returns:
        List of study codes with registered URLs
    """
    from .studies import get_study_urlpatterns
    
    studies = []
    for pattern in get_study_urlpatterns():
        # Extract study code from pattern
        if hasattr(pattern, 'pattern'):
            path_str = str(pattern.pattern)
            if path_str.startswith('studies/'):
                code = path_str.replace('studies/', '').rstrip('/')
                studies.append(code)
    
    return studies


def refresh_urls():
    """
    Refresh study URLs without restart.
    
    Call this after adding new studies dynamically.
    """
    from .studies import refresh_study_urls
    
    global urlpatterns
    
    # Remove old study patterns
    urlpatterns = [p for p in urlpatterns if not _is_study_pattern(p)]
    
    # Add refreshed study patterns
    urlpatterns.extend(refresh_study_urls())


def _is_study_pattern(pattern) -> bool:
    """Check if URL pattern is a study pattern."""
    if hasattr(pattern, 'pattern'):
        return str(pattern.pattern).startswith('studies/')
    return False