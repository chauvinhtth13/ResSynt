# backend\api\base\views.py (login section only)
import logging
from typing import Optional, Dict, Any, Tuple

from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _, get_language, activate
from django.db.models import Q
from django.db import connections
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.cache import cache
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponse
from typing import Union

# Axes imports
from axes.helpers import get_client_str
from axes.models import AccessAttempt
from axes.conf import settings as axes_settings
from axes.handlers.proxy import AxesProxyHandler

# Local imports
from backend.tenancy.models import Study
from .login import UsernameOrEmailAuthenticationForm
from .constants import LoginMessages, SessionKeys

logger = logging.getLogger(__name__)
User = get_user_model()
axes_handler = AxesProxyHandler()

class LoginService:
    """Service class to handle login logic and reduce code duplication"""
    
    @staticmethod
    def get_actual_username(username_input: str) -> Optional[str]:
        """Convert email to username if needed"""
        if not username_input:
            return None
            
        if "@" in username_input:
            try:
                user = User.objects.only('username').get(email__iexact=username_input)
                return user.username
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None
        
        return username_input if User.objects.filter(username__iexact=username_input).exists() else None
    
    @staticmethod
    def check_account_status(request, actual_username: Optional[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if account is locked and return status
        Returns: (is_locked, error_context)
        """
        if not actual_username:
            return False, {}
        
        # Check if account is locked by axes
        if axes_handler.is_locked(request, {'username': actual_username}):
            return True, {
                'error_message': LoginMessages.ACCOUNT_LOCKED,
            }
        
        return False, {}
    
    @staticmethod
    def get_login_error_context(actual_username: Optional[str]) -> Dict[str, Any]:
        """
        Get error context based on login attempt
        Simplified: same message for non-existent user and wrong password
        """
        if not actual_username:
            # Don't reveal that user doesn't exist
            return {
                'error_message': LoginMessages.INVALID_CREDENTIALS,
            }
        
        # Check attempt count
        try:
            attempt = AccessAttempt.objects.filter(username=actual_username).first()
            if attempt:
                failures = attempt.failures_since_start
                limit = axes_settings.AXES_FAILURE_LIMIT
                remaining = max(0, limit - failures)
                
                if remaining <= 0:
                    return {
                        'error_message': LoginMessages.ACCOUNT_LOCKED,
                    }
                
                # Show warning if more than 1 attempt
                if failures > 1 and remaining > 0:
                    return {
                        'error_message': LoginMessages.ACCOUNT_WILL_BE_LOCKED.format(remaining),
                    }
        except Exception as e:
            logger.error(f"Error checking attempts for {actual_username}: {e}")
        
        # Default message for first wrong attempt
        return {
            'error_message': LoginMessages.INVALID_CREDENTIALS,
        }
    
    @staticmethod
    def clear_user_cache(username: str) -> None:
        """Clear all cached data for a user"""
        if not username:
            return
        
        cache_keys = [
            f'user_exists_{username}',
            f'user_attempts_{username}',
            f'user_actual_{username}',
            f'axes_attempts_{username}',
        ]
        cache.delete_many(cache_keys)

@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def custom_login(request: HttpRequest) -> Union[HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponse]:
    """
    Optimized login view with simplified messages:
    1. Invalid credentials: "Invalid username or password. Please try again."
    2. Multiple failures: "Incorrect login. Account will be locked in X attempts."
    3. Account locked: "Account locked. Please contact support."
    """
    # Set Vietnamese as default
    if not get_language():
        activate('vi')
        request.session['django_language'] = 'vi'

    # Redirect if authenticated
    if request.user.is_authenticated:
        return redirect('admin:index' if request.user.is_superuser else 'select_study')

    context: Dict[str, Any] = {}
    
    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        actual_username = LoginService.get_actual_username(username_input) if username_input else None
        
        # Check if account is locked first (only if user exists to avoid info leakage)
        is_locked, lock_context = LoginService.check_account_status(request, actual_username)
        if is_locked:
            form = UsernameOrEmailAuthenticationForm(request)
            context.update(lock_context)
            context['form'] = form
            return render(request, 'authentication/login.html', context)
        
        # Proceed with form validation (authentication)
        form = UsernameOrEmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Successful login
            user = form.get_user()
            
            # Clear session data
            request.session.pop(SessionKeys.LAST_USERNAME, None)
            
            # Clear cache for this user
            LoginService.clear_user_cache(user.username)

            # Login and redirect
            login(request, user)
            logger.info(f"User {user.pk} ({user.username}) logged in successfully")
            
            next_url = request.GET.get('next', '')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('admin:index' if user.is_superuser else 'select_study')
        else:
            # Failed login - get appropriate error message
            if username_input:
                # Store for GET request (e.g., refresh)
                request.session[SessionKeys.LAST_USERNAME] = username_input
                
                # Get error context
                error_context = LoginService.get_login_error_context(actual_username)
                context.update(error_context)
            
            context['form'] = form
    else:
        # GET request
        form = UsernameOrEmailAuthenticationForm(request)
        
        # Check if returning from failed attempt
        last_username = request.session.get(SessionKeys.LAST_USERNAME)
        if last_username:
            form.initial['username'] = last_username
            
            # Check if account is now locked
            actual_username = LoginService.get_actual_username(last_username)
            is_locked, lock_context = LoginService.check_account_status(request, actual_username)
            if is_locked:
                context.update(lock_context)
        
        context['form'] = form

    return render(request, 'authentication/login.html', context)

@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def select_study(request):
    # """Handle study selection for authenticated users, redirect superusers to admin."""
    if request.GET.get('clear') or 'clear_study' in request.POST:
        request.session.pop('current_study', None)
        logger.info(f"Cleared current_study for user {request.user.pk} on select_study access.")

    if request.user.is_superuser:
        logger.info(f"Superuser {request.user.pk} bypassing study selection.")
        return redirect('admin:index')

    # Set default language to Vietnamese if not set
    # Set language with Vietnamese as default
    language = get_language()
    if not language or language not in [lang[0] for lang in settings.LANGUAGES]:
        language = 'vi'  # Default to Vietnamese
        activate(language)
        request.session['django_language'] = language


    # Chỉ lấy các nghiên cứu user có quyền truy cập và status là active
    studies_qs = (
        Study.objects
        .filter(memberships__user=request.user, memberships__is_active=True, status=Study.Status.ACTIVE)
        .select_related()
        .distinct()
        .order_by('code')
        .prefetch_related('translations')
        .only('id', 'code', 'db_name', 'created_at', 'updated_at', 'status')
    )

    # Apply search filter if query exists
    if query := request.GET.get('q', '').strip():
        studies_qs = studies_qs.filter(
            Q(code__icontains=query) |
            Q(translations__language_code=language, translations__name__icontains=query)
        )

    studies = list(studies_qs)
    for study in studies:
        study.set_current_language(language)

    context = {
        'studies': studies,
        'error': None,
        'is_superuser': request.user.is_superuser,
    }

    # Handle study selection
    if request.method == 'POST':
        if study_id := request.POST.get('study_id'):
            try:
                study = next(s for s in studies if str(s.pk) == study_id)
                request.session['current_study'] = study.pk
                logger.info(f"User {request.user.pk} selected study {study.code}")
                return redirect('dashboard')  # Redirect to dashboard after selection
            except StopIteration:
                logger.warning(f"Invalid study selection attempt by user {request.user.pk}: {study_id}")
                context['error'] = _("Invalid study selection.")

    return render(request, 'default/select_study.html', context)

@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def dashboard(request, study_code=None):
    # Ensure Vietnamese is set
    language = get_language()
    if not language or language not in [lang[0] for lang in settings.LANGUAGES]:
        language = 'vi'
        activate(language)
        request.session['django_language'] = language

    # """Render the dashboard for the selected study."""
    study = getattr(request, 'study', None)
    if not study:
        logger.warning(f"No study selected for user {request.user.pk}; redirecting to select_study.")
        return redirect('select_study')

    # Derive study folder from db_name (e.g., 'db_study_43en' -> 'study_43en')
    study_folder = study.db_name.replace('db_', '', 1) if study.db_name.startswith('db_') else study.db_name

    # Fetch table names from study database (all user tables)
    tables = []
    if 'access_data' in getattr(request, 'study_permissions', set()):
        try:
            with connections[study.db_name].cursor() as cursor:
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = %s
                    ORDER BY tablename
                """, [study.search_path or 'data'])
                tables = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Fetched {len(tables)} tables from {study.db_name} for user {request.user.pk}")
        except Exception as e:
            logger.error(f"Error fetching tables from {study.db_name}: {e}")
            tables = []

    context = {
        'study_folder': study_folder,
        'tables': tables,
    }
    return render(request, 'default/dashboard.html', context)

@login_required
@never_cache
def logout_view(request):
    """Simple logout view"""
    if request.user.is_authenticated:
        username = request.user.username
        logger.info(f"User {username} logged out")
        
        # Clear user cache
        LoginService.clear_user_cache(username)
    
    # Clear all session data
    request.session.flush()
    logout(request)
    
    return redirect('/')