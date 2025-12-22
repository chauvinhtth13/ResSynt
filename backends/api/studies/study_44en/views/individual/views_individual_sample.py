# backends/api/studies/study_44en/views/individual/views_individual_sample.py

"""
Individual Sample Views for Study 44EN
Handles sample collection and food frequency data
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.individual import (
    Individual, Individual_Sample, Individual_FoodFrequency
)
from backends.studies.study_44en.forms.individual import (
    Individual_SampleForm, Individual_FoodFrequencyForm
)
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


@login_required
def individual_sample(request, subjectid):
    """
    Manage individual sample and food frequency data
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get or create sample record
    try:
        sample = Individual_Sample.objects.get(SUBJECTID=individual)
        sample_is_create = False
    except Individual_Sample.DoesNotExist:
        sample = None
        sample_is_create = True
    
    # Get or create food frequency record
    try:
        food_frequency = Individual_FoodFrequency.objects.get(SUBJECTID=individual)
        food_is_create = False
    except Individual_FoodFrequency.DoesNotExist:
        food_frequency = None
        food_is_create = True
    
    if request.method == 'POST':
        sample_form = Individual_SampleForm(
            request.POST,
            instance=sample,
            prefix='sample'
        )
        food_frequency_form = Individual_FoodFrequencyForm(
            request.POST,
            instance=food_frequency,
            prefix='food'
        )
        
        if sample_form.is_valid() and food_frequency_form.is_valid():
            try:
                with transaction.atomic():
                    # Save sample
                    sample = sample_form.save(commit=False)
                    sample.SUBJECTID = individual
                    set_audit_metadata(sample, request.user)
                    sample.save()
                    
                    logger.info(
                        f"{'Created' if sample_is_create else 'Updated'} "
                        f"sample for {subjectid}"
                    )
                    
                    # Save food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.SUBJECTID = individual
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    
                    logger.info(
                        f"{'Created' if food_is_create else 'Updated'} "
                        f"food frequency for {subjectid}"
                    )
                    
                    messages.success(
                        request,
                        f'Sample data for {subjectid} saved successfully.'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"Error saving sample data: {e}", exc_info=True)
                messages.error(request, f'Error saving sample data: {str(e)}')
        else:
            # Log validation errors
            if sample_form.errors:
                logger.warning(f"Sample form errors: {sample_form.errors}")
            if food_frequency_form.errors:
                logger.warning(f"Food frequency form errors: {food_frequency_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
        sample_form = Individual_SampleForm(
            instance=sample,
            prefix='sample'
        )
        food_frequency_form = Individual_FoodFrequencyForm(
            instance=food_frequency,
            prefix='food'
        )
    
    context = {
        'individual': individual,
        'sample_form': sample_form,
        'food_frequency_form': food_frequency_form,
        'sample_is_create': sample_is_create,
        'food_is_create': food_is_create,
    }
    
    return render(request, 'studies/study_44en/individual/sample.html', context)


__all__ = ['individual_sample']
