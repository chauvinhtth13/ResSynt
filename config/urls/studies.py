"""
Dynamic Study URL Registration.

Registers API endpoints for each active study at startup.
"""
import logging
from typing import List, Tuple

from django.urls import URLPattern, path, include

logger = logging.getLogger(__name__)


def get_study_api_modules() -> List[Tuple[str, str]]:
    """
    Get list of study API modules to register.
    
    Returns:
        List of (study_code, module_path) tuples
        
    Example:
        [('43EN', 'backends.api.studies.study_43en.urls'), ...]
    """
    try:
        from backends.studies.study_loader import get_api_modules
        return get_api_modules() or []
    except ImportError:
        logger.warning("study_loader not available - no study APIs registered")
        return []
    except Exception as e:
        logger.error(f"Error loading study modules: {type(e).__name__}")
        return []


def register_study_urls() -> List[URLPattern]:
    """
    Register URL patterns for all active studies.
    
    Returns:
        List of URL patterns for studies
    """
    api_modules = get_study_api_modules()
    
    if not api_modules:
        logger.info("No study APIs to register")
        return []
    
    registered = []
    failed = []
    
    for study_code, api_module in api_modules:
        try:
            url_pattern = path(
                f'studies/{study_code}/',
                include(api_module)
            )
            registered.append(url_pattern)
            
        except ImportError as e:
            failed.append(study_code)
            logger.error(f"Cannot import API module for study {study_code}: {e}")
        except Exception as e:
            failed.append(study_code)
            logger.error(f"Error registering study {study_code}: {type(e).__name__}: {e}")
    
    # Summary logging
    if registered:
        logger.info(f"Registered {len(registered)} study API(s)")
    
    if failed:
        logger.warning(f"Failed to register {len(failed)} study API(s): {', '.join(failed)}")
    
    return registered


# Cache registered URLs (computed once at import)
_study_urlpatterns: List[URLPattern] = []
_initialized = False


def get_study_urlpatterns() -> List[URLPattern]:
    """
    Get study URL patterns (lazy initialization).
    
    Returns:
        List of study URL patterns
    """
    global _study_urlpatterns, _initialized
    
    if not _initialized:
        _study_urlpatterns = register_study_urls()
        _initialized = True
    
    return _study_urlpatterns


def refresh_study_urls() -> List[URLPattern]:
    """
    Force refresh of study URLs.
    
    Useful after adding new studies without restarting.
    
    Returns:
        Updated list of URL patterns
    """
    global _study_urlpatterns, _initialized
    
    _initialized = False
    _study_urlpatterns = []
    
    return get_study_urlpatterns()