# backends/api/studies/study_44en/views/household/views_household_exposure.py

"""
Household Exposure Views for Study 44EN
Handles exposure, water sources, treatments, and animals
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.household import (
    HH_CASE, HH_Exposure, HH_WaterSource, HH_WaterTreatment, HH_Animal,
    HH_FoodFrequency, HH_FoodSource
)
from backends.studies.study_44en.forms.household import (
    HH_ExposureForm,
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
def household_exposure(request, hhid):
    """
    Manage household exposure data with water and animal formsets
    """
    queryset = get_filtered_households(request.user)
    household = get_object_or_404(queryset, HHID=hhid)
    
    # Get or create exposure record
    try:
        exposure = HH_Exposure.objects.get(HHID=household)
        is_create = False
    except HH_Exposure.DoesNotExist:
        exposure = None
        is_create = True
    
    # Get or create food records
    try:
        food_freq = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_freq = None
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    if request.method == 'POST':
        exposure_form = HH_ExposureForm(request.POST, instance=exposure)
        food_freq_form = HH_FoodFrequencyForm(request.POST, instance=food_freq)
        food_source_form = HH_FoodSourceForm(request.POST, instance=food_source)
        
        if all([
            exposure_form.is_valid(),
            food_freq_form.is_valid(),
            food_source_form.is_valid()
        ]):
            try:
                with transaction.atomic():
                    # Save exposure
                    exposure = exposure_form.save(commit=False)
                    exposure.HHID = household
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    
                    logger.info(f"{'Created' if is_create else 'Updated'} exposure for {hhid}")
                    
                    # Parse and save water sources from static template fields
                    # Clear existing water sources for this household
                    HH_WaterSource.objects.filter(HHID=exposure).delete()
                    
                    source_types = {
                        'tap': HH_WaterSource.SourceTypeChoices.TAP,
                        'bottle': HH_WaterSource.SourceTypeChoices.BOTTLED,
                        'well': HH_WaterSource.SourceTypeChoices.WELL,
                        'rain': HH_WaterSource.SourceTypeChoices.RAIN,
                        'river': HH_WaterSource.SourceTypeChoices.RIVER,
                        'pond': HH_WaterSource.SourceTypeChoices.POND,
                        'other': HH_WaterSource.SourceTypeChoices.OTHER,
                    }
                    
                    for source_key, source_type in source_types.items():
                        # Check if ANY checkbox is ticked for this source
                        drink = request.POST.get(f'water_{source_key}_drink') == 'on'
                        use = request.POST.get(f'water_{source_key}_use') == 'on'
                        irrigate = request.POST.get(f'water_{source_key}_irrigate') == 'on'
                        other_purpose = request.POST.get(f'water_{source_key}_other', '').strip()
                        
                        # Only create record if at least one purpose is selected
                        if drink or use or irrigate or other_purpose:
                            ws = HH_WaterSource(
                                HHID=exposure,
                                SOURCE_TYPE=source_type,
                                DRINKING=drink,
                                LIVING=use,
                                IRRIGATION=irrigate,
                                OTHER=bool(other_purpose),
                                OTHER_PURPOSE=other_purpose if other_purpose else None
                            )
                            set_audit_metadata(ws, request.user)
                            ws.save()
                            logger.info(f"Created water source: {source_type}")
                    
                    # Parse and save water treatment from radio button
                    # Clear existing treatments
                    HH_WaterTreatment.objects.filter(HHID=exposure).delete()
                    
                    treatment_method = request.POST.get('TREATMENT_METHOD', '').strip()
                    if treatment_method:
                        treatment_other_text = request.POST.get('TREATMENT_METHOD_OTHER', '').strip()
                        wt = HH_WaterTreatment(
                            HHID=exposure,
                            TREATMENT_TYPE=treatment_method,
                            TREATMENT_TYPE_OTHER=treatment_other_text if treatment_other_text else None
                        )
                        set_audit_metadata(wt, request.user)
                        wt.save()
                        logger.info(f"Created water treatment: {treatment_method}")
                    
                    # Parse and save animals from static template fields
                    # Clear existing animals for this household
                    HH_Animal.objects.filter(HHID=exposure).delete()
                    
                    animal_types = {
                        'dog': HH_Animal.AnimalTypeChoices.DOG,
                        'cat': HH_Animal.AnimalTypeChoices.CAT,
                        'bird': HH_Animal.AnimalTypeChoices.BIRD,
                        'poultry': HH_Animal.AnimalTypeChoices.POULTRY,
                        'cow': HH_Animal.AnimalTypeChoices.COW,
                        'other': HH_Animal.AnimalTypeChoices.OTHER,
                    }
                    
                    animal_count = 0
                    for animal_key, animal_type in animal_types.items():
                        if request.POST.get(f'animal_{animal_key}') == 'on':
                            other_text = request.POST.get('animal_other_text', '').strip() if animal_key == 'other' else None
                            animal = HH_Animal(
                                HHID=exposure,
                                ANIMAL_TYPE=animal_type,
                                ANIMAL_TYPE_OTHER=other_text if other_text else None
                            )
                            set_audit_metadata(animal, request.user)
                            animal.save()
                            animal_count += 1
                            logger.info(f"Created animal: {animal_type}")
                    
                    logger.info(f"Saved {animal_count} animals")
                    
                    # Save food frequency
                    food_freq = food_freq_form.save(commit=False)
                    food_freq.HHID = household
                    set_audit_metadata(food_freq, request.user)
                    food_freq.save()
                    logger.info(f"Saved food frequency")
                    
                    # Save food source
                    food_source = food_source_form.save(commit=False)
                    food_source.HHID = household
                    set_audit_metadata(food_source, request.user)
                    food_source.save()
                    logger.info(f"Saved food source")
                    
                    messages.success(
                        request,
                        f'Exposure data for household {hhid} saved successfully.'
                    )
                    return redirect('study_44en:household:detail', hhid=hhid)
                    
            except Exception as e:
                logger.error(f"Error saving exposure: {e}", exc_info=True)
                messages.error(request, f'Error saving exposure: {str(e)}')
        else:
            # Log validation errors
            if exposure_form.errors:
                logger.warning(f"Exposure form errors: {exposure_form.errors}")
            if food_freq_form.errors:
                logger.warning(f"Food frequency form errors: {food_freq_form.errors}")
            if food_source_form.errors:
                logger.warning(f"Food source form errors: {food_source_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
        exposure_form = HH_ExposureForm(instance=exposure)
        food_freq_form = HH_FoodFrequencyForm(instance=food_freq)
        food_source_form = HH_FoodSourceForm(instance=food_source)
    
    # Load saved water sources, treatment, and animals for template
    water_data = {}
    treatment_method = None
    treatment_other = None
    animal_data = {}
    
    if exposure:
        # Get all water sources for this household
        water_sources = HH_WaterSource.objects.filter(HHID=exposure)
        for ws in water_sources:
            source_key = ws.SOURCE_TYPE  # 'tap', 'bottled', 'well', etc.
            # Map 'bottled' to 'bottle' for template field names
            if source_key == 'bottled':
                source_key = 'bottle'
            
            water_data[f'water_{source_key}_drink'] = ws.DRINKING
            water_data[f'water_{source_key}_use'] = ws.LIVING
            water_data[f'water_{source_key}_irrigate'] = ws.IRRIGATION
            water_data[f'water_{source_key}_other'] = ws.OTHER_PURPOSE or ''
        
        # Get water treatment (only 1 record expected)
        treatment = HH_WaterTreatment.objects.filter(HHID=exposure).first()
        if treatment:
            treatment_method = treatment.TREATMENT_TYPE
            treatment_other = treatment.TREATMENT_TYPE_OTHER or ''
        
        # Get all animals for this household
        animals = HH_Animal.objects.filter(HHID=exposure)
        for animal in animals:
            animal_type = animal.ANIMAL_TYPE
            animal_data[animal_type] = True
            if animal_type == 'other' and animal.ANIMAL_TYPE_OTHER:
                animal_data['other_text'] = animal.ANIMAL_TYPE_OTHER
    
    context = {
        'household': household,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': is_create,
        'water_data': water_data,
        'treatment_method': treatment_method,
        'treatment_other': treatment_other,
        'animal_data': animal_data,
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)


__all__ = ['household_exposure']
