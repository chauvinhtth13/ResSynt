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
from .services import LoginService, StudyService
from .helpers import (
    build_dashboard_context,
    add_sites_to_context,
    get_user_studies_list,
    get_study_folder_path,
)
from .login import UsernameOrEmailAuthenticationForm

logger = logging.getLogger(__name__)


# ============================================
# AUTHENTICATION VIEWS
# ============================================
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
@ensure_language
@set_language_on_response
def custom_login(request: HttpRequest) -> HttpResponse:
    """
    Login view with username or email support.
    Handles account locking via Django-Axes.
    """
    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect('admin:index' if request.user.is_superuser else 'select_study')

    context: Dict[str, Any] = {
        'LANGUAGE_CODE': translation.get_language() or AppConstants.DEFAULT_LANGUAGE
    }
    
    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        actual_username = LoginService.get_actual_username(username_input) if username_input else None
        
        # Check locks before authentication
        if actual_username:
            is_locked, lock_context = LoginService.check_account_status(request, actual_username)
            if is_locked:
                form = UsernameOrEmailAuthenticationForm(request)
                form.initial['username'] = username_input
                context['form'] = form
                context.update(lock_context)
                logger.warning(f"Blocked access attempt for {actual_username}")
                return render(request, 'authentication/login.html', context)
        
        # Process authentication
        try:
            form = UsernameOrEmailAuthenticationForm(request, data=request.POST)
            
            if form.is_valid():
                user = form.get_user()
                
                if not user.is_active:
                    context['form'] = form
                    context['error_message'] = LoginMessages.ACCOUNT_LOCKED
                    return render(request, 'authentication/login.html', context)
                
                # Clear session and cache
                request.session.pop(SessionKeys.LAST_FAILED_USERNAME, None)
                LoginService.clear_user_cache(user.username)

                # Login user
                login(request, user)
                logger.debug(f"User {user.username} logged in successfully")
                
                # Redirect to next URL or default
                next_url = request.GET.get('next', '')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('admin:index' if user.is_superuser else 'select_study')
            else:
                # Handle invalid form
                if username_input:
                    request.session[SessionKeys.LAST_FAILED_USERNAME] = username_input
                    context.update(LoginService.get_login_error_context(actual_username))
                context['form'] = form
                
        except AxesBackendPermissionDenied:
            logger.warning(f"AxesBackendPermissionDenied for {username_input}")
            form = UsernameOrEmailAuthenticationForm(request)
            form.initial['username'] = username_input
            context['form'] = form
            context['error_message'] = LoginMessages.ACCOUNT_LOCKED
            
    else:
        # GET request
        form = UsernameOrEmailAuthenticationForm(request)
        
        # Check if returning from failed attempt
        last_username = request.session.get(SessionKeys.LAST_FAILED_USERNAME)
        if last_username:
            form.initial['username'] = last_username
            actual_username = LoginService.get_actual_username(last_username)
            is_locked, lock_context = LoginService.check_account_status(request, actual_username)
            if is_locked:
                context.update(lock_context)
        
        context['form'] = form

    return render(request, 'authentication/login.html', context)


@login_required
@never_cache
def logout_view(request):
    """Logout view - clears session and cache"""
    if request.user.is_authenticated:
        username = request.user.username
        logger.debug(f"User {username} logged out")
        LoginService.clear_user_cache(username)
    
    request.session.flush()
    logout(request)
    
    return redirect('/')


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
                    next_url = request.GET.get('next', 'dashboard')
                    return redirect(reverse(next_url))
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
    
    # Get user permissions and sites from middleware
    user_permissions = getattr(request, 'study_permissions', set())
    user_site_codes = list(getattr(request, 'study_sites', []))
    
    # Set current language on study
    current_lang = translation.get_language() or AppConstants.DEFAULT_LANGUAGE
    study.set_current_language(current_lang)
    
    # Build base context
    context = build_dashboard_context(
        request, study, user_membership, user_permissions, user_site_codes
    )
    
    # Add sites information
    add_sites_to_context(context, study, user_membership, current_lang, request)
    
    # Add user studies for study switcher
    context['user_studies'] = get_user_studies_list(request.user, current_lang)
    
    # Add study folder path
    context['study_folder'] = get_study_folder_path(study.code)
    
    logger.debug(f"Dashboard loaded successfully for user {request.user.pk}")
    
    return render(request, 'default/dashboard.html', context)