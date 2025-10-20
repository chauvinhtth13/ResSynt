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
from axes.handlers.proxy import AxesProxyHandler

from backends.tenancy.models import StudyMembership

# Local imports
from .constants import AppConstants, LoginMessages, SessionKeys
from .decorators import ensure_language, set_language_on_response
from .services import LoginService, StudyService

from .login import UsernameOrEmailAuthenticationForm

logger = logging.getLogger(__name__)
axes_handler = AxesProxyHandler()


# ============================================
# AUTHENTICATION VIEWS
# ============================================
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def custom_login(request):
    """
    FIXED VERSION - Guaranteed to return response
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.error("=" * 50)
    logger.error(f"LOGIN VIEW CALLED")
    logger.error(f"Path: {request.path}")
    logger.error(f"Method: {request.method}")
    logger.error(f"User authenticated: {request.user.is_authenticated}")
    logger.error("=" * 50)
    
    # Redirect if authenticated
    if request.user.is_authenticated:
        logger.error("User authenticated - redirecting")
        return redirect('select_study')
    
    # GET request - show form
    if request.method == 'GET':
        logger.error("GET request - rendering form")
        from .login import UsernameOrEmailAuthenticationForm
        form = UsernameOrEmailAuthenticationForm(request)
        
        response = render(request, 'authentication/login.html', {
            'form': form,
            'LANGUAGE_CODE': 'vi'
        })
        
        logger.error(f"GET response created: {type(response)}")
        logger.error(f"GET response status: {response.status_code}")
        
        return response  # ← EXPLICIT RETURN
    
    # POST request - process login
    logger.error("POST request - processing login")
    username = request.POST.get('username', '').strip()
    
    logger.error(f"Username input: {username}")
    
    # Empty username
    if not username:
        logger.error("Empty username - returning error")
        from .login import UsernameOrEmailAuthenticationForm
        form = UsernameOrEmailAuthenticationForm(request)
        
        response = render(request, 'authentication/login.html', {
            'form': form,
            'error_message': 'Please enter username',
            'LANGUAGE_CODE': 'vi'
        })
        
        logger.error(f"Empty username response: {type(response)}")
        return response  # ← EXPLICIT RETURN
    
    # Check if account is locked BEFORE authentication
    from .services import LoginService
    actual_username = LoginService.get_actual_username(username)
    
    if actual_username:
        is_locked, lock_context = LoginService.check_lockout_status(actual_username, request)
        
        if is_locked:
            logger.error(f"Account locked: {actual_username}")
            from .login import UsernameOrEmailAuthenticationForm
            form = UsernameOrEmailAuthenticationForm(request)
            form.initial['username'] = username
            
            context = {
                'form': form,
                'LANGUAGE_CODE': 'vi'
            }
            context.update(lock_context)
            
            response = render(request, 'authentication/login.html', context)
            response.status_code = 403
            
            logger.error(f"Locked response: {type(response)}, status: {response.status_code}")
            return response  # ← EXPLICIT RETURN
    
    # Try authentication
    from .login import UsernameOrEmailAuthenticationForm
    form = UsernameOrEmailAuthenticationForm(request, data=request.POST)
    
    logger.error(f"Form valid: {form.is_valid()}")
    
    # Valid - login user
    if form.is_valid():
        logger.error("Form valid - logging in")
        from django.contrib.auth import login
        user = form.get_user()
        login(request, user)
        
        logger.error(f"User logged in: {user.username}")
        return redirect('select_study')  # ← EXPLICIT RETURN
    
    # Invalid - show errors
    logger.error("Form invalid - showing errors")
    logger.error(f"Form errors: {form.errors}")
    
    # Get remaining attempts
    if actual_username:
        remaining = LoginService.get_remaining_attempts(actual_username)
        logger.error(f"Remaining attempts: {remaining}")
        
        context = {
            'form': form,
            'error_message': 'Invalid credentials',
            'LANGUAGE_CODE': 'vi'
        }
        
        if remaining > 0:
            context['remaining_attempts'] = remaining
            if remaining <= 2:
                context['warning_message'] = f"Warning: {remaining} attempts remaining"
        else:
            # Just got locked
            context['error_message'] = 'Account locked due to too many failed attempts'
            context['form_disabled'] = True
            context['is_locked'] = True
    else:
        context = {
            'form': form,
            'error_message': 'Invalid credentials',
            'LANGUAGE_CODE': 'vi'
        }
    
    response = render(request, 'authentication/login.html', context)
    
    logger.error(f"Invalid form response: {type(response)}")
    logger.error(f"Invalid form status: {response.status_code}")
    logger.error("RETURNING response now")  # ← NEW LOG
    
    return response 
    

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
    
    # # Build base context
    # context = build_dashboard_context(
    #     request, study, user_membership, user_permissions, user_site_codes
    # )
    
    # # Add sites information
    # add_sites_to_context(context, study, user_membership, current_lang, request)
    
    # # Add user studies for study switcher
    # context['user_studies'] = get_user_studies_list(request.user, current_lang)
    
    # # Add study folder path
    # context['study_folder'] = get_study_folder_path(study.code)
    
    
    
    logger.debug(f"Dashboard loaded successfully for user {request.user.pk}")
    
    return render(request, 'default/dashboard.html',)