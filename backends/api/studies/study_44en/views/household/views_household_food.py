# backends/api/studies/study_44en/views/household/views_household_food.py

"""
Household Food Views for Study 44EN
Handles food frequency and food source data
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.household import (
    HH_CASE, HH_FoodFrequency, HH_FoodSource
)
from backends.studies.study_44en.forms.household import (
    HH_FoodFrequencyForm, HH_FoodSourceForm
)
from backends.api.studies.study_44en.views.views_base import get_filtered_households

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


@login_required
def household_food(request, hhid):
    """
    Manage household food frequency and source data
    """
    queryset = get_filtered_households(request.user)
    household = get_object_or_404(queryset, HHID=hhid)
    
    # Get or create food frequency record
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
        freq_is_create = False
    except HH_FoodFrequency.DoesNotExist:
        food_frequency = None
        freq_is_create = True
    
    # Get or create food source record
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
        source_is_create = False
    except HH_FoodSource.DoesNotExist:
        food_source = None
        source_is_create = True
    
    if request.method == 'POST':
        food_frequency_form = HH_FoodFrequencyForm(
            request.POST,
            instance=food_frequency,
            prefix='frequency'
        )
        food_source_form = HH_FoodSourceForm(
            request.POST,
            instance=food_source,
            prefix='source'
        )
        
        if food_frequency_form.is_valid() and food_source_form.is_valid():
            try:
                with transaction.atomic():
                    # Save food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.HHID = household
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    
                    logger.info(
                        f"{'Created' if freq_is_create else 'Updated'} "
                        f"food frequency for {hhid}"
                    )
                    
                    # Save food source
                    food_source = food_source_form.save(commit=False)
                    food_source.HHID = household
                    set_audit_metadata(food_source, request.user)
                    food_source.save()
                    
                    logger.info(
                        f"{'Created' if source_is_create else 'Updated'} "
                        f"food source for {hhid}"
                    )
                    
                    messages.success(
                        request,
                        f'Food data for household {hhid} saved successfully.'
                    )
                    return redirect('study_44en:household:detail', hhid=hhid)
                    
            except Exception as e:
                logger.error(f"Error saving food data: {e}", exc_info=True)
                messages.error(request, f'Error saving food data: {str(e)}')
        else:
            # Log validation errors
            if food_frequency_form.errors:
                logger.warning(f"Food frequency form errors: {food_frequency_form.errors}")
            if food_source_form.errors:
                logger.warning(f"Food source form errors: {food_source_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
        food_frequency_form = HH_FoodFrequencyForm(
            instance=food_frequency,
            prefix='frequency'
        )
        food_source_form = HH_FoodSourceForm(
            instance=food_source,
            prefix='source'
        )
    
    context = {
        'household': household,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'freq_is_create': freq_is_create,
        'source_is_create': source_is_create,
    }
    
    return render(request, 'studies/study_44en/household/food.html', context)


__all__ = ['household_food']
