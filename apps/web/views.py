# apps/web/views.py
"""
Views for ResSync Platform web app.
Handles study selection and custom login with language and tenancy support.
"""
import logging
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _, get_language, activate
from django.db.models import Q
from django.views.decorators.cache import never_cache  # Ensure imported
from django.db import connections
from django.conf import settings
from apps.tenancy.models import Study, StudyMembership
from .login import UsernameOrEmailAuthenticationForm

logger = logging.getLogger('apps.web')

@never_cache
@login_required
def select_study(request):
    """Handle study selection for authenticated users, redirect superusers to admin."""
    if request.GET.get('clear') or 'clear_study' in request.POST:
        request.session.pop('current_study', None)
        logger.info(f"Cleared current_study for user {request.user.pk} on select_study access.")

    if request.user.is_superuser:
        logger.info(f"Superuser {request.user.pk} bypassing study selection.")
        return redirect('admin:index')

    # Set default language to Vietnamese if not set
    if not request.session.get('django_language'):
        request.session['django_language'] = 'vi'
        activate('vi')
    language = get_language()

    # Fetch unique studies the user has access to
    studies_qs = (
        Study.objects
        .filter(memberships__user=request.user)
        .distinct()
        .order_by('code')
        .prefetch_related('translations')
    )

    # Apply search filter if query exists
    if query := request.GET.get('q', '').strip():
        studies_qs = studies_qs.filter(
            Q(code__icontains=query) |
            Q(translations__language_code=language, translations__name__icontains=query) |
            Q(translations__language_code=language, translations__introduction__icontains=query)
        )

    studies = list(studies_qs)  # Materialize for set_current_language

    # Set translation language for studies
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
def custom_login(request):
    """Custom login view redirecting superusers to admin and others to study selection."""
    if request.user.is_authenticated:
        return redirect('admin:index' if request.user.is_superuser else 'select_study')

    form = UsernameOrEmailAuthenticationForm(request, data=request.POST) if request.method == 'POST' else UsernameOrEmailAuthenticationForm()
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        logger.info(f"User {user.pk} logged in.")
        return redirect('admin:index' if user.is_superuser else 'select_study')

    return render(request, 'default/login.html', {'form': form})

@never_cache
@login_required
def dashboard(request, study_code=None):
    """Render the dashboard for the selected study."""
    study = getattr(request, 'study', None)
    if not study:
        logger.warning(f"No study selected for user {request.user.pk}; redirecting to select_study.")
        return redirect('select_study')

    # Derive study folder from db_name (e.g., 'db_study_43en' -> 'study_43en')
    study_folder = study.db_name.replace('db_', '', 1) if study.db_name.startswith('db_') else study.db_name

    # Fetch table names from study database (all user tables)
    tables = []
    if 'access_data' in getattr(request, 'study_permissions', set()):
        with connections[study.db_name].cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            """)
            tables = [row[0] for row in cursor.fetchall()]
        logger.debug(f"Fetched {len(tables)} tables from {study.db_name} for user {request.user.pk}")

    context = {
        'study_folder': study_folder,
        'tables': tables,
    }
    return render(request, 'default/dashboard.html', context)