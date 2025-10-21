# backend/api/base/views.py
"""
Views for authentication and dashboard
Clean and maintainable - business logic moved to services
"""
import logging
from typing import Dict, Any
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import HttpRequest, HttpResponse
from django.utils import translation, timezone
from django.db import transaction, models

from axes.exceptions import AxesBackendPermissionDenied
from axes.handlers.proxy import AxesProxyHandler

from backends.tenancy.models.user import User

# Local imports
from .constants import AppConstants, LoginMessages, SessionKeys
from .decorators import ensure_language, set_language_on_response
from .services import LoginService, StudyService
from .login import UsernameOrEmailAuthenticationForm

logger = logging.getLogger(__name__)
axes_handler = AxesProxyHandler()


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
@ensure_language
@set_language_on_response
def custom_login(request: HttpRequest) -> HttpResponse:
    """
    Login view với auto-deactivate khi lockout.
    """
    # Fast path: already authenticated
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin:index')
        return redirect('select_study')
    
    # Initialize context
    context: Dict[str, Any] = {
        'LANGUAGE_CODE': translation.get_language() or AppConstants.DEFAULT_LANGUAGE
    }
    
    # GET request - display form
    if request.method == 'GET':
        context['form'] = UsernameOrEmailAuthenticationForm(request)
        return render(request, 'authentication/login.html', context)
    
    # POST request - process login
    username_input = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    
    # Validate input
    if not username_input or not password:
        context['form'] = UsernameOrEmailAuthenticationForm(request)
        context['error_message'] = LoginMessages.INVALID_CREDENTIALS
        return render(request, 'authentication/login.html', context)
    
    # Convert email to username if needed
    actual_username = LoginService.get_actual_username(username_input)
    
    if actual_username:
        # CHECK 1: Is user already deactivated?
        try:
            user = User.objects.only('is_active').get(username=actual_username)
            if not user.is_active:
                # User is deactivated (could be manual or from previous lockout)
                form = UsernameOrEmailAuthenticationForm(request)
                form.initial['username'] = username_input
                
                context.update({
                    'form': form,
                    'error_message': LoginMessages.ACCOUNT_LOCKED,
                    'form_disabled': True,
                    'is_locked': True,
                })
                
                logger.warning(f"Deactivated account login attempt: {actual_username}")
                response = render(request, 'authentication/login.html', context)
                response.status_code = 403
                return response
        except User.DoesNotExist:
            pass
        
        # CHECK 2: Is user locked by Axes (7+ failures)?
        if LoginService.is_user_locked(actual_username):
            # Deactivate user if not already deactivated
            LoginService.deactivate_locked_user(actual_username, request)
            
            form = UsernameOrEmailAuthenticationForm(request)
            form.initial['username'] = username_input
            
            context.update({
                'form': form,
                'error_message': LoginMessages.ACCOUNT_LOCKED,
                'form_disabled': True,
                'is_locked': True,
            })
            
            logger.warning(f"Axes-locked account login attempt: {actual_username}")
            response = render(request, 'authentication/login.html', context)
            response.status_code = 403
            return response
    
    # Try authentication
    form = UsernameOrEmailAuthenticationForm(request, data=request.POST)
    
    if form.is_valid():
        # Authentication successful
        user = form.get_user()
        
        # Double-check user is active (shouldn't happen but safety check)
        if not user.is_active:
            context.update({
                'form': form,
                'error_message': LoginMessages.ACCOUNT_INACTIVE,
                'form_disabled': True,
            })
            response = render(request, 'authentication/login.html', context)
            response.status_code = 403
            return response
        
        # Log user in
        login(request, user)
        LoginService.clear_user_cache(user.username)
        
        # Reset failure counters on successful login
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.save(update_fields=['failed_login_attempts', 'last_failed_login'])
        
        logger.info(f"Successful login: {user.username}")
        
        # Handle redirect
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        
        if user.is_superuser:
            return redirect('admin:index')
        return redirect('select_study')
    
    # Authentication failed
    if actual_username:
        # Increment failure counter in User model
        with transaction.atomic():
            User.objects.filter(username=actual_username).update(
                failed_login_attempts=models.F('failed_login_attempts') + 1,
                last_failed_login=timezone.now()
            )
        
        # Check if NOW locked after this failure
        if LoginService.is_user_locked(actual_username):
            # Just hit 7 failures - deactivate user
            LoginService.deactivate_locked_user(actual_username, request)
            
            form = UsernameOrEmailAuthenticationForm(request)
            form.initial['username'] = username_input
            
            context.update({
                'form': form,
                'error_message': LoginMessages.ACCOUNT_LOCKED,
                'form_disabled': True,
                'is_locked': True,
            })
            
            logger.critical(f"Account locked and deactivated after failed attempt: {actual_username}")
            response = render(request, 'authentication/login.html', context)
            response.status_code = 403
            return response
        
        # Not locked yet - show progressive warning
        failures = LoginService.get_failure_count(actual_username)
        remaining = 7 - failures
        
        if remaining <= 2:
            error_message = LoginMessages.ACCOUNT_WILL_BE_LOCKED.format(remaining)
            is_warning = True
        else:
            error_message = LoginMessages.INVALID_CREDENTIALS
            is_warning = False
    else:
        # Username not found
        error_message = LoginMessages.INVALID_CREDENTIALS
        is_warning = False
    
    # Show error on same page
    form = UsernameOrEmailAuthenticationForm(request)
    form.initial['username'] = username_input
    
    context.update({
        'form': form,
        'error_message': error_message,
        'is_warning': is_warning if actual_username else False,
    })
    
    logger.warning(f"Failed login: {username_input}")
    return render(request, 'authentication/login.html', context)



@login_required
@never_cache
def logout_view(request: HttpRequest) -> HttpResponse:
    """Logout and clear cache"""
    if request.user.is_authenticated:
        username = request.user.username
        LoginService.clear_user_cache(username)
        logger.info(f"User logged out: {username}")
    
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

    return render(request, 'default/dashboard.html', {})