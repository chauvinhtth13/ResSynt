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
def individual_list(request):
    """
    List all individuals with search and filter
    """
    queryset = get_filtered_individuals(request.user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(SUBJECTID__icontains=search_query) |
            Q(SITEID__icontains=search_query) |
            Q(HHID__icontains=search_query)
        )
    
    # Ordering
    order_by = request.GET.get('order_by', '-ENR_DATE')
    queryset = queryset.order_by(order_by)
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    
    try:
        individuals = paginator.page(page)
    except PageNotAnInteger:
        individuals = paginator.page(1)
    except EmptyPage:
        individuals = paginator.page(paginator.num_pages)
    
    context = {
        'individuals': individuals,
        'search_query': search_query,
        'total_count': queryset.count(),
    }
    
    return render(request, 'studies/study_44en/CRF/base/individual_list.html', context)

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
        'followups',
        'samples'
    ).get(pk=individual_id)


__all__ = [
    'get_filtered_individuals',
    'household_list',
    'individual_list',
    'get_household_with_related',
    'get_individual_with_related',
]
