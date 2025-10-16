# backend/api/base/services/study_service.py
"""
Service layer for study-related operations
"""
import logging
from typing import List
from django.core.cache import cache
from django.db.models import Q
from django.utils import translation

from backends.tenancy.models import Study
from ..constants import AppConstants, CacheKeys

logger = logging.getLogger(__name__)


class StudyService:
    """Service for study-related operations"""
    
    @staticmethod
    def get_user_studies(user, search_query: str = '') -> List[Study]:
        """
        Get studies for user with caching and search capability.
        
        Args:
            user: User object
            search_query: Optional search term
            
        Returns:
            List of Study objects the user has access to
        """
        # Check cache first
        cache_key = CacheKeys.get_user_studies(user.pk, search_query)
        cached_studies = cache.get(cache_key)
        
        if cached_studies is not None:
            logger.debug(f"Cache hit for user studies: {user.pk}")
            return cached_studies
        
        # Query database
        studies = (
            Study.objects
            .filter(
                memberships__user=user,
                memberships__is_active=True,
                status__in=[Study.Status.ACTIVE, Study.Status.ARCHIVED]
            )
            .select_related('created_by')
            .prefetch_related('translations')
            .distinct()
            .order_by('code')
        )
        
        # Apply search filter if provided
        if search_query:
            current_lang = translation.get_language() or AppConstants.DEFAULT_LANGUAGE
            studies = studies.filter(
                Q(code__icontains=search_query) |
                Q(translations__language_code=current_lang, translations__name__icontains=search_query)
            )
        
        # Convert to list and set language
        studies = list(studies)
        for study in studies:
            study.set_current_language(AppConstants.DEFAULT_LANGUAGE)
        
        # Cache the results
        cache.set(cache_key, studies, AppConstants.CACHE_TIMEOUT)
        logger.debug(f"Cached user studies for: {user.pk}")
        
        return studies
    
    @staticmethod
    def clear_study_session(session) -> None:
        """
        Clear all study-related session data.
        
        Args:
            session: Django session object
        """
        for key in AppConstants.STUDY_SESSION_KEYS:
            session.pop(key, None)
        session.modified = True
        logger.debug("Cleared study session data")
    
    @staticmethod
    def set_study_session(session, study) -> None:
        """
        Set study information in session.
        
        Args:
            session: Django session object
            study: Study object
        """
        session.update({
            'current_study': study.pk,
            'current_study_code': study.code,
            'current_study_db': study.db_name,
        })
        session.modified = True
        logger.debug(f"Set study in session: {study.code} (ID: {study.pk})")
    
    @staticmethod
    def recover_study_from_session(request):
        """
        Attempt to recover study from session when middleware fails.
        
        Args:
            request: HTTP request object
            
        Returns:
            Study object or None
        """
        current_study_id = request.session.get('current_study')
        
        if not current_study_id:
            return None
        
        try:
            study = Study.objects.select_related('created_by').get(
                id=current_study_id,
                memberships__user=request.user,
                memberships__is_active=True,
                status__in=[Study.Status.ACTIVE, Study.Status.ARCHIVED]
            )
            
            # Set study on request
            request.study = study
            request.study_code = study.code
            request.study_id = study.pk
            
            # Update DB connection
            from backends.tenancy.db_router import set_current_db
            from backends.tenancy.db_loader import study_db_manager
            set_current_db(study.db_name)
            study_db_manager.add_study_db(study.db_name)
            
            logger.debug(f"Successfully recovered study: {study.code}")
            return study
            
        except Study.DoesNotExist:
            logger.error(f"Study ID {current_study_id} not found or user has no access")
            return None
        except Exception as e:
            logger.error(f"Failed to recover study: {e}", exc_info=True)
            return None