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
from apps.tenancy.models import StudyMembership
from .login import UsernameOrEmailAuthenticationForm

logger = logging.getLogger('apps.web')

@login_required
def select_study(request):
    """Handle study selection for authenticated users, redirect superusers to admin."""
    if request.user.is_superuser:
        logger.info(f"Superuser {request.user.pk} bypassing study selection.")
        return redirect('admin:index')

    # Set default language to Vietnamese if not set
    if not request.session.get('django_language'):
        request.session['django_language'] = 'vi'
        activate('vi')
    language = get_language()

    # Fetch and filter study memberships
    memberships = (
        StudyMembership.objects
        .filter(user=request.user)
        .select_related('study', 'role')
        .prefetch_related('study__translations')
        .order_by('study__code')
        .distinct()
    )

    # Apply search filter if query exists
    if query := request.GET.get('q', '').strip():
        memberships = memberships.filter(
            Q(study__code__icontains=query) |
            Q(study__translations__language_code=language, study__translations__name__icontains=query) |
            Q(study__translations__language_code=language, study__translations__introduction__icontains=query)
        )

    # Set translation language for studies
    for membership in memberships:
        membership.study.set_current_language(language)

    context = {
        'studies': memberships,
        'error': None,
        'is_superuser': request.user.is_superuser,
    }

    # Handle study selection
    if request.method == 'POST':
        if study_id := request.POST.get('study_id'):
            try:
                membership = next(m for m in memberships if str(m.study.pk) == study_id)
                request.session['current_study'] = membership.study.pk
                logger.info(f"User {request.user.pk} selected study {membership.study.code}")
                return redirect('home')  # Replace with 'dashboard' when defined
            except StopIteration:
                logger.warning(f"Invalid study selection attempt by user {request.user.pk}: {study_id}")
                context['error'] = _("Invalid study selection.")

    return render(request, 'default/select_study.html', context)

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