# backend/api/base/views.py
"""
Views for authentication and dashboard
Clean and maintainable - business logic moved to services
"""
import logging
from typing import Dict, Any
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import HttpRequest, HttpResponse
from django.utils import translation
from django.urls import reverse

from axes.exceptions import AxesBackendPermissionDenied

from backends.tenancy.models import StudyMembership

# Local imports
from .constants import AppConstants, LoginMessages, SessionKeys
from .decorators import ensure_language, set_language_on_response
from .services import StudyService

logger = logging.getLogger(__name__)


# ============================================
# STUDY SELECTION VIEW
# ============================================
@never_cache
@login_required
@require_http_methods(["GET", "POST"])
@ensure_language
@set_language_on_response
def select_study(request):
    """
    Study selection view.
    Allows users to choose which study to work with.
    """
    # Clear study if requested
    if request.GET.get('clear') or request.POST.get('clear_study'):
        StudyService.clear_study_session(request.session)
        logger.debug(f"Cleared study selection for user {request.user.pk}")

    # Superusers go to admin
    if request.user.is_superuser:
        return redirect('admin:index')

    # Get user's studies with optional search
    query = request.GET.get('q', '').strip()
    studies = StudyService.get_user_studies(request.user, query)

    context = {
        'studies': studies,
        'query': query,
        'current_study_id': request.session.get(SessionKeys.CURRENT_STUDY),
    }

    # Handle POST - study selection
    if request.method == 'POST':
        study_id = request.POST.get('study_id')
        
        if study_id:
            try:
                study_id = int(study_id)
                study = next((s for s in studies if s.pk == study_id), None)
                
                if study:
                    # Setup session with study info
                    StudyService.set_study_session(request.session, study)
                    logger.debug(f"User {request.user.pk} selected study {study.code}")
                    
                    # Redirect to next URL or dashboard
                    next_url = request.GET.get('next')
                    if next_url:
                        try:
                            return redirect(reverse(next_url))
                        except Exception as e:
                            logger.warning(f"Cannot reverse '{next_url}': {e}")
                    
                    # Fallback: construct URL from study code
                    study_code_lower = study.code.lower()
                    # Direct URL: /studies/{study_code}/dashboard/
                    dashboard_url = f'/studies/{study_code_lower}/dashboard/'
                    logger.info(f"Redirecting to direct URL: {dashboard_url}")
                    return redirect(dashboard_url)
                else:
                    context['error_message'] = LoginMessages.NO_STUDY_ACCESS
                    
            except (ValueError, TypeError):
                context['error_message'] = LoginMessages.INVALID_STUDY
    return render(request, 'default/select_study.html', context)


# ============================================
# DASHBOARD VIEW
# ============================================
@never_cache
@login_required
@require_http_methods(["GET", "POST"])
@ensure_language
@set_language_on_response
def dashboard(request):
    """
    Main dashboard view.
    Displays study information, user permissions, and accessible sites.
    """
    logger.debug(f"Dashboard accessed by user {request.user.pk}")
    
    # Get study from middleware or recover from session
    study = getattr(request, 'study', None)
    if not study:
        study = StudyService.recover_study_from_session(request)
    
    if not study:
        logger.error("No study found, redirecting to select_study")
        return redirect(reverse('select_study'))
    
    logger.debug(f"Loaded study: {study.code} (id={study.pk})")
    
    # Get user membership
    user_membership = StudyMembership.objects.filter(
        user=request.user,
        study=study,
        is_active=True
    ).select_related('group').first() 
    
    if not user_membership:
        logger.warning(f"User {request.user.pk} has no active membership in study {study.pk}")
        return redirect('select_study')
    

    logger.debug(f"Dashboard loaded successfully for user {request.user.pk}")
    
    return render(request, 'default/dashboard.html', {})