# backends/api/studies/study_44en/views/individual/views_individual_case.py

"""
Individual Case Views for Study 44EN
Handles Individual CRUD operations
"""

import logging
from datetime import date
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.individual import Individual
from backends.studies.study_44en.forms.individual import IndividualForm
from backends.api.studies.study_44en.views.views_base import (
    get_filtered_individuals, get_individual_with_related
)

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


@login_required
def individual_list(request):
    """
    List all individuals with search, filter, and pagination
    """
    from backends.api.studies.study_44en.views.views_base import individual_list
    return individual_list(request)


@login_required
def individual_detail(request, subjectid):
    """
    View individual details with all related data
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get related counts
    exposure_count = individual.exposures.count() if hasattr(individual, 'exposures') else 0
    followup_count = individual.followups.count() if hasattr(individual, 'followups') else 0
    sample_count = individual.samples.count() if hasattr(individual, 'samples') else 0
    
    context = {
        'individual': individual,
        'exposure_count': exposure_count,
        'followup_count': followup_count,
        'sample_count': sample_count,
    }
    
    return render(request, 'studies/study_44en/individual/detail.html', context)


@login_required
def individual_create(request):
    """
    Create new individual
    """
    if request.method == 'POST':
        individual_form = IndividualForm(request.POST)
        
        if individual_form.is_valid():
            try:
                with transaction.atomic():
                    # Save individual
                    individual = individual_form.save(commit=False)
                    set_audit_metadata(individual, request.user)
                    individual.save()
                    
                    logger.info(f"Created individual: {individual.SUBJECTID}")
                    
                    messages.success(
                        request,
                        f'Individual {individual.SUBJECTID} created successfully.'
                    )
                    return redirect('study_44en:individual:detail', subjectid=individual.SUBJECTID)
                    
            except Exception as e:
                logger.error(f"Error creating individual: {e}", exc_info=True)
                messages.error(request, f'Error saving individual: {str(e)}')
        else:
            # Log validation errors
            if individual_form.errors:
                logger.warning(f"Individual form errors: {individual_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show blank form
        initial_data = {'ENR_DATE': date.today()}
        individual_form = IndividualForm(initial=initial_data)
    
    context = {
        'individual_form': individual_form,
        'is_create': True,
    }
    
    return render(request, 'studies/study_44en/individual/form.html', context)


@login_required
def individual_edit(request, subjectid):
    """
    Edit existing individual
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    if request.method == 'POST':
        individual_form = IndividualForm(request.POST, instance=individual)
        
        if individual_form.is_valid():
            try:
                with transaction.atomic():
                    # Update individual
                    individual = individual_form.save(commit=False)
                    set_audit_metadata(individual, request.user)
                    individual.save()
                    
                    logger.info(f"Updated individual: {individual.SUBJECTID}")
                    
                    messages.success(
                        request,
                        f'Individual {individual.SUBJECTID} updated successfully.'
                    )
                    return redirect('study_44en:individual:detail', subjectid=individual.SUBJECTID)
                    
            except Exception as e:
                logger.error(f"Error updating individual: {e}", exc_info=True)
                messages.error(request, f'Error updating individual: {str(e)}')
        else:
            # Log validation errors
            if individual_form.errors:
                logger.warning(f"Individual form errors: {individual_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
        individual_form = IndividualForm(instance=individual)
    
    context = {
        'individual_form': individual_form,
        'individual': individual,
        'is_create': False,
    }
    
    return render(request, 'studies/study_44en/individual/form.html', context)


__all__ = [
    'individual_list',
    'individual_detail',
    'individual_create',
    'individual_edit',
]
