#  BETTER: Single dynamic registration

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
import logging

logger = logging.getLogger(__name__)

# Base URLs
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False), name='home'),
    path("accounts/", include("allauth.urls")),
    path('', include('backends.api.base.urls')),    
]

#  Dynamic study URL registration
def register_study_urls():
    """Register all study URLs dynamically"""
    try:
        from backends.studies.study_loader import get_api_modules
        
        api_modules = get_api_modules()
        
        if not api_modules:
            logger.info("No study APIs to register")
            return []
        
        logger.info(f"Registering {len(api_modules)} study API(s)")
        
        registered_urls = []
        for study_code, api_module in api_modules:
            try:
                url_path = f'studies/{study_code}/'
                url_pattern = path(url_path, include(api_module))
                
                registered_urls.append(url_pattern)
                logger.debug(f" Registered: {url_path} -> {api_module}")
                
            except ImportError as e:
                logger.error(f"❌ Cannot import {api_module}: {e}")
            except Exception as e:
                logger.error(f"❌ Error registering {study_code}: {e}")
        
        return registered_urls
        
    except ImportError as e:
        logger.error(f"❌ Cannot import study_loader: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return []

# Register study URLs
study_urls = register_study_urls()
urlpatterns.extend(study_urls)

# Static files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)