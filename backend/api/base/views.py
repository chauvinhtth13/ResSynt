# backend\api\base\views.py (login section only)
import logging
from datetime import timedelta
from typing import Optional, Dict, Any
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _, get_language, activate
from django.db.models import Q
from django.db import connections
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.cache import cache
from django.conf import settings

# Axes imports
from axes.models import AccessAttempt
from axes.conf import settings as axes_settings
from axes.handlers.proxy import AxesProxyHandler
from axes.helpers import get_client_username

# Local imports
from backend.tenancy.models import Study, StudyMembership
from .login import UsernameOrEmailAuthenticationForm

logger = logging.getLogger(__name__)

# Initialize Axes handler (proxy ensures middleware context)
axes_handler = AxesProxyHandler()

# Cache keys
CACHE_PREFIX = "ressync_"


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def custom_login(request):
    """
    Enhanced login view with better Axes integration.
    Shows remaining attempts and lockout messages.
    """
    # Set Vietnamese as default for login page
    if not get_language():
        activate('vi')
        request.session['django_language'] = 'vi'

    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect('admin:index' if request.user.is_superuser else 'select_study')

    # Initialize context
    context: Dict[str, Any] = {}

    if request.method == 'POST':
        form = UsernameOrEmailAuthenticationForm(request, data=request.POST)
        username = request.POST.get('username', '')
        if username:
            request.session['last_failed_username'] = username
        credentials = None
        if username:
            credentials = {'username': username}
            is_locked = axes_handler.is_locked(request, credentials)
            if is_locked:
                # Show lockout as error_message and do not redirect
                error_message = _("Account locked: too many login attempts. Please contact support to unlock your account.")
                context['error_message'] = error_message
                lockout_info = get_lockout_details(username)
                if lockout_info is not None:
                    context['lockout_info'] = lockout_info
                context['form'] = form
                return render(request, 'authentication/login.html', context)
        if form.is_valid():
            user = form.get_user()
            if username:
                clear_user_attempts(username)
                request.session.pop('last_failed_username', None)
            login(request, user)
            logger.info(f"User {user.pk} logged in successfully.")
            return redirect('admin:index' if user.is_superuser else 'select_study')
        else:
            # Custom error message logic
            error_message = None
            if username:
                attempts_info = get_attempts_info(username)
                if attempts_info is not None:
                    context['attempts_info'] = attempts_info
                    failures = attempts_info.get('failures', 0)
                    limit = attempts_info.get('limit', 5)
                    remaining = attempts_info.get('remaining', limit)
                    if failures <= 2:
                        error_message = _("Failed login. Please verify and reenter your username and password.")
                    elif failures >= 3 and remaining > 0:
                        error_message = _(f"Failed login. Your account will be blocked after {remaining} failed login attempts!")
                if credentials is not None:
                    is_locked = axes_handler.is_locked(request, credentials)
                    if is_locked:
                        # Show lockout as error_message and do not redirect
                        error_message = _("Account locked: too many login attempts. Please contact support to unlock your account.")
                        context['error_message'] = error_message
                        lockout_info = get_lockout_details(username)
                        if lockout_info is not None:
                            context['lockout_info'] = lockout_info
            context['form'] = form
            context['error_message'] = error_message
    else:
        # GET request
        form = UsernameOrEmailAuthenticationForm(request)
        # Check if there's a stored username from previous attempt
        last_username = request.session.get('last_failed_username', '')
        if last_username:
            # Pre-fill the form
            form.initial['username'] = last_username
            # Get attempts info
            attempts_info = get_attempts_info(last_username)
            if attempts_info is not None:
                context['attempts_info'] = attempts_info
            # Check if locked
            credentials = {'username': last_username}
            is_locked = axes_handler.is_locked(request, credentials)
            if is_locked:
                lockout_info = get_lockout_details(last_username)
                if lockout_info is not None:
                    context['lockout_info'] = lockout_info
        context['form'] = form

    return render(request, 'authentication/login.html', context)


def get_lockout_details(username: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed lockout information for a username.
    """
    if not username:
        return None
    
    try:
        # Get the latest attempt
        attempt = AccessAttempt.objects.filter(
            username=username
        ).latest('attempt_time')
        
        # Calculate unlock time
        cooloff_time = axes_settings.AXES_COOLOFF_TIME
        
        if isinstance(cooloff_time, int):
            cooloff_delta = timedelta(hours=cooloff_time)
        elif isinstance(cooloff_time, timedelta):
            cooloff_delta = cooloff_time
        else:
            cooloff_delta = timedelta(hours=1)  # Default
            
        unlock_time = attempt.attempt_time + cooloff_delta
        time_remaining = unlock_time - timezone.now()
        
        if time_remaining.total_seconds() > 0:
            return {
                'username': username,
                'unlock_time': unlock_time,
                'time_remaining': time_remaining,
                'time_remaining_str': format_time_remaining(time_remaining),
                'attempts': attempt.failures_since_start,
            }
    except AccessAttempt.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error getting lockout details for {username}: {e}")
    
    return None


def get_attempts_info(username: str) -> Optional[Dict[str, Any]]:
    """
    Get information about login attempts for a username.
    """
    if not username:
        return None
    
    try:
        # Get attempt count
        attempt = AccessAttempt.objects.filter(
            username=username
        ).order_by('-attempt_time').first()
        
        if attempt:
            failures = attempt.failures_since_start
            limit = axes_settings.AXES_FAILURE_LIMIT
            remaining = max(0, limit - failures)
            
            return {
                'username': username,
                'failures': failures,
                'limit': limit,
                'remaining': remaining,
                'is_warning': remaining <= 2,
                'is_critical': remaining <= 1,
            }
    except Exception as e:
        logger.error(f"Error getting attempts info for {username}: {e}")
    
    return None


def clear_user_attempts(username: str) -> None:
    """
    Clear failed login attempts for a user.
    """
    if not username:
        return
    
    try:
        # Clear from database
        AccessAttempt.objects.filter(username=username).delete()
        
        # Clear from cache
        cache.delete_many([
            f"{CACHE_PREFIX}attempts_{username}",
            f"{CACHE_PREFIX}locked_{username}"
        ])
        
        logger.info(f"Cleared login attempts for {username}")
    except Exception as e:
        logger.error(f"Error clearing attempts for {username}: {e}")


def format_time_remaining(time_remaining: timedelta) -> str:
    """
    Format time remaining in a human-readable format.
    """
    if not time_remaining:
        return "a few seconds"
    
    total_seconds = int(time_remaining.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if hours == 0 and minutes == 0 and seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    
    return " and ".join(parts) if parts else "a few seconds"

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

def logout_view(request):
    """Logout view"""
    if request.user.is_authenticated:
        username = request.user.username
        logger.info(f"User {username} logged out")
    
    logout(request)
    return redirect('home')