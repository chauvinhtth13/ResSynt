# backends/api/studies/study_44en/views/views_base.py

"""
Base Views for Study 44EN
Provides common functionality for household and individual views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse

from backends.studies.study_44en.models.household import (
    HH_CASE, HH_Member, HH_Exposure, HH_WaterSource,
    HH_WaterTreatment, HH_Animal, HH_FoodFrequency, HH_FoodSource
)
from backends.studies.study_44en.models.individual import (
    Individual, Individual_Exposure, Individual_FoodFrequency,
    Individual_FollowUp, Individual_Sample
)

from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    require_crf_delete,
)



def get_filtered_households(user):
    """
    Get all households (single site study)
    """
    return HH_CASE.objects.all().select_related().prefetch_related('members')


def get_filtered_individuals(user):
    """
    Get all individuals (single site study)
    """
    return Individual.objects.all().select_related()


@login_required
@require_crf_view('dashboard')
def dashboard(request):
    """
    Dashboard view for Study 44EN
    """
    # Get summary statistics
    total_households = HH_CASE.objects.count()
    total_members = HH_Member.objects.count()
    total_individuals = Individual.objects.count()
    total_followups = Individual_FollowUp.objects.count()
    total_samples = Individual_Sample.objects.count()
    
    # Get recent data
    recent_households = HH_CASE.objects.order_by('-last_modified_at')[:5]
    recent_individuals = Individual.objects.select_related('MEMBERID').order_by('-last_modified_at')[:5]
    
    context = {
        'total_households': total_households,
        'total_members': total_members,
        'total_individuals': total_individuals,
        'total_followups': total_followups,
        'total_samples': total_samples,
        'recent_households': recent_households,
        'recent_individuals': recent_individuals,
    }
    
    return render(request, 'studies/study_44en/dashboard.html', context)


@login_required
@require_crf_view('hh_case')
def household_list(request):
    """
    List all households with search and filter
    """
    queryset = get_filtered_households(request.user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(HHID__icontains=search_query) |
            Q(WARD__icontains=search_query) |
            Q(CITY__icontains=search_query)
        )
    
    # Ordering
    order_by = request.GET.get('order_by', '-last_modified_at')
    queryset = queryset.order_by(order_by)
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    
    try:
        households = paginator.page(page)
    except PageNotAnInteger:
        households = paginator.page(1)
    except EmptyPage:
        households = paginator.page(paginator.num_pages)
    
    context = {
        'households': households,
        'search_query': search_query,
        'total_count': queryset.count(),
    }
    
    return render(request, 'studies/study_44en/CRF/base/household_list.html', context)


@login_required
@require_crf_view('individual')
def individual_list(request):
    """
    List all individuals with search and filter
    """
    queryset = get_filtered_individuals(request.user).select_related('MEMBERID', 'MEMBERID__HHID')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(MEMBER__MEMBERID__icontains=search_query) |
            Q(INITIALS__icontains=search_query) |
            Q(MEMBER__FIRST_NAME__icontains=search_query) |
            Q(MEMBER__LAST_NAME__icontains=search_query)
        )
    
    # Annotate with counts
    queryset = queryset.annotate(
        followup_count=Count('follow_ups', distinct=True),
        sample_count=Count('samples', distinct=True)
    )
    
    # Ordering
    order_by = request.GET.get('order_by', '-last_modified_at')
    queryset = queryset.order_by(order_by)
    
    # Calculate summary stats
    total_count = queryset.count()
    exposure_count = queryset.filter(exposure__isnull=False).count()
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    
    try:
        individuals = paginator.page(page)
    except PageNotAnInteger:
        individuals = paginator.page(1)
    except EmptyPage:
        individuals = paginator.page(paginator.num_pages)
    
    # Add has_exposure to each individual
    for individual in individuals:
        individual.has_exposure = hasattr(individual, 'exposure') and individual.exposure is not None
    
    context = {
        'individuals': individuals,
        'search_query': search_query,
        'total_count': total_count,
        'exposure_count': exposure_count,
        'followup_count': queryset.filter(followup_count__gt=0).count(),
        'sample_count': queryset.filter(sample_count__gt=0).count(),
    }
    
    return render(request, 'studies/study_44en/CRF/individual/list.html', context)

def get_household_with_related(household_id):
    """
    Get household with all related data
    """
    return HH_CASE.objects.prefetch_related(
        'members',
        'exposures',
        'water_sources',
        'water_treatments',
        'animals',
        'food_frequencies',
        'food_sources'
    ).get(pk=household_id)


def get_individual_with_related(individual_id):
    """
    Get individual with all related data
    """
    return Individual.objects.prefetch_related(
        'exposures',
        'water_sources',
        'water_treatments',
        'comorbidities',
        'vaccines',
        'hospitalizations',
        'medications',
        'travel_history',
        'symptoms',
        'food_frequencies',
        'follow_ups',
        'samples'
    ).get(pk=individual_id)


__all__ = [
    'dashboard',
    'get_filtered_households',
    'get_filtered_individuals',
    'household_list',
    'individual_list',
    'get_household_with_related',
    'get_individual_with_related',
]
