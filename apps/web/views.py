# apps/web/views.py
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.tenancy.models import StudyMembership, Study

logger = logging.getLogger('apps.web')

@login_required
def select_study(request):
    """
    View to list and select a study for the authenticated user.
    - GET: Display filtered list of user's studies based on query param 'q'.
    - POST: Set selected study in session and redirect to dashboard.
    """
    user = request.user
    memberships = StudyMembership.objects.filter(user=user).select_related('study', 'role')

    # Handle search filtering on GET
    query = request.GET.get('q', '').strip()
    if query:
        memberships = memberships.filter(
            Q(study__code__icontains=query) |
            Q(study__name__icontains=query) |
            Q(study__introduction__icontains=query)
        )

    # Prepare context with studies (memberships)
    context = {
        'studies': memberships,
        'error': None,
    }

    # Handle POST: Select study
    if request.method == 'POST':
        study_id = request.POST.get('study_id')
        if study_id:
            try:
                membership = memberships.get(study__id=study_id)
                request.session['current_study'] = membership.study.pk
                logger.info(f"User {user.pk} selected study {membership.study.code}")
                return redirect('dashboard')  # Redirect to dashboard or home after selection
            except StudyMembership.DoesNotExist:
                logger.warning(f"Invalid study selection attempt by user {user.pk}: {study_id}")
                # Optionally add error message
                context['error'] = "Invalid study selection."

    return render(request, 'default/select_study.html', context)