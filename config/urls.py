# config/urls.py - FIXED ERROR HANDLING

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
import logging

logger = logging.getLogger(__name__)

# Base patterns
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("secret-admin/", admin.site.urls),
    path('', include('backends.api.base.urls')),
]

# Dynamically load study API URLs
try:
    from backends.studies.study_loader import get_api_modules
    
    api_modules = get_api_modules()  # Now always returns list
    
    if api_modules:
        logger.info(f"Loading {len(api_modules)} study API(s)")
        
        for study_code, api_module in api_modules:
            try:
                # Create URL path
                url_path = f'studies/{study_code.upper()}/'
                
                # Add to urlpatterns
                urlpatterns.append(
                    path(url_path, include(api_module, namespace=f'study_{study_code}'))
                )
                
                logger.info(f"Registered API: /{url_path} -> {api_module}")
                
            except ImportError as e:
                logger.error(f"Cannot import API module {api_module}: {e}")
            except Exception as e:
                logger.error(f"Error registering API for {study_code}: {e}")
    else:
        logger.info("No study APIs to register")
        
except ImportError as e:
    logger.error(f"Cannot import study_loader: {e}")
except Exception as e:
    logger.error(f"Unexpected error loading study APIs: {e}")

# Static/Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Log final URL configuration
logger.info(f"Total URL patterns: {len(urlpatterns)}")