# backends/api/studies/study_44en/views/views_dashboard.py

"""
Dashboard and Statistics Views for Study 44EN
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from datetime import datetime, timedelta

from backends.studies.study_44en.models.household import HH_CASE, HH_Member
from backends.studies.study_44en.models.individual import Individual, Individual_FollowUp
from .views_base import get_filtered_households, get_filtered_individuals
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    require_crf_delete,
)



@login_required
@require_crf_view('dashboard')
def dashboard_44en(request):
    """
    Main dashboard for Study 44EN
    Shows summary statistics and recent activities
    """
    # Get filtered querysets based on user's site access
    households = get_filtered_households(request.user)
    individuals = get_filtered_individuals(request.user)
    
    # Calculate statistics
    total_households = households.count()
    total_individuals = individuals.count()
    
    # Members statistics
    total_members = HH_Member.objects.filter(
        HHID__in=households.values_list('HHID', flat=True)
    ).count()
    
    # Recent enrollments (last 30 days) - using last_modified_at
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    recent_households = households.filter(last_modified_at__gte=thirty_days_ago).count()
    recent_individuals = individuals.filter(last_modified_at__gte=thirty_days_ago).count()
    
    # Follow-up statistics
    total_followups = Individual_FollowUp.objects.filter(
        MEMBERID__in=individuals.values_list('MEMBERID', flat=True)
    ).count()
    
    # Pending follow-ups (scheduled but not completed)
    pending_followups = Individual_FollowUp.objects.filter(
        MEMBERID__in=individuals.values_list('MEMBERID', flat=True),
        ASSESSMENT_DATE__isnull=True
    ).count()
    
    # Recent households (last 10) - using last_modified_at
    recent_household_list = households.order_by('-last_modified_at')[:10]
    
    # Recent individuals (last 10) - using last_modified_at
    recent_individual_list = individuals.order_by('-last_modified_at')[:10]
    
    context = {
        'total_households': total_households,
        'total_individuals': total_individuals,
        'total_members': total_members,
        'total_followups': total_followups,
        'pending_followups': pending_followups,
        'recent_households_count': recent_households,
        'recent_individuals_count': recent_individuals,
        'recent_household_list': recent_household_list,
        'recent_individual_list': recent_individual_list,
    }
    
    return render(request, 'studies/study_44en/dashboard.html', context)


__all__ = ['dashboard_44en']
