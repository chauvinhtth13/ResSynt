# backends/api/studies/study_44en/views/household/views_household_exposure.py

"""
Household Exposure Views for Study 44EN
Handles exposure, water sources, treatments, and animals

REFACTORED: Separated CREATE and UPDATE following household_case pattern
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
from .helpers import (
    get_household_with_related,
    set_audit_metadata,
    make_form_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS (Specific to exposure)
# ==========================================

def _save_water_sources(request, exposure):
    """
    Parse and save water sources from POST data
    
    Returns:
        int: Number of water sources saved
    """
    # Clear existing
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
    
    count = 0
    for source_key, source_type in source_types.items():
        drink = request.POST.get(f'water_{source_key}_drink') == 'on'
        use = request.POST.get(f'water_{source_key}_use') == 'on'
        irrigate = request.POST.get(f'water_{source_key}_irrigate') == 'on'
        other_purpose = request.POST.get(f'water_{source_key}_other', '').strip()
        
        # Only create if at least one purpose selected
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
            count += 1
            logger.info(f"Saved water source: {source_type}")
    
    logger.info(f"Saved {count} water sources")
    return count


def _save_water_treatment(request, exposure):
    """
    Parse and save water treatment from POST data
    
    Returns:
        bool: True if treatment saved, False otherwise
    """
    # Clear existing
    HH_WaterTreatment.objects.filter(HHID=exposure).delete()
    
    treatment_method = request.POST.get('TREATMENT_METHOD', '').strip()
    if treatment_method:
        treatment_other = request.POST.get('TREATMENT_METHOD_OTHER', '').strip()
        wt = HH_WaterTreatment(
            HHID=exposure,
            TREATMENT_TYPE=treatment_method,
            TREATMENT_TYPE_OTHER=treatment_other if treatment_other else None
        )
        set_audit_metadata(wt, request.user)
        wt.save()
        logger.info(f"Saved water treatment: {treatment_method}")
        return True
    return False


def _save_animals(request, exposure):
    """
    Parse and save animals from POST data
    
    Returns:
        int: Number of animals saved
    """
    # Clear existing
    HH_Animal.objects.filter(HHID=exposure).delete()
    
    animal_types = {
        'dog': HH_Animal.AnimalTypeChoices.DOG,
        'cat': HH_Animal.AnimalTypeChoices.CAT,
        'bird': HH_Animal.AnimalTypeChoices.BIRD,
        'poultry': HH_Animal.AnimalTypeChoices.POULTRY,
        'cow': HH_Animal.AnimalTypeChoices.COW,
        'other': HH_Animal.AnimalTypeChoices.OTHER,
    }
    
    count = 0
    for animal_key, animal_type in animal_types.items():
        if request.POST.get(f'animal_{animal_key}') == 'on':
            other_text = None
            if animal_key == 'other':
                other_text = request.POST.get('animal_other_text', '').strip()
            
            animal = HH_Animal(
                HHID=exposure,
                ANIMAL_TYPE=animal_type,
                ANIMAL_TYPE_OTHER=other_text if other_text else None
            )
            set_audit_metadata(animal, request.user)
            animal.save()
            count += 1
            logger.info(f"Saved animal: {animal_type}")
    
    logger.info(f"Saved {count} animals")
    return count


def _load_water_data(exposure):
    """Load water sources data for template"""
    water_data = {}
    
    water_sources = HH_WaterSource.objects.filter(HHID=exposure)
    for ws in water_sources:
        source_key = ws.SOURCE_TYPE
        # Map 'bottled' to 'bottle' for template field names
        if source_key == 'bottled':
            source_key = 'bottle'
        
        water_data[f'water_{source_key}_drink'] = ws.DRINKING
        water_data[f'water_{source_key}_use'] = ws.LIVING
        water_data[f'water_{source_key}_irrigate'] = ws.IRRIGATION
        water_data[f'water_{source_key}_other'] = ws.OTHER_PURPOSE or ''
    
    return water_data


def _load_treatment_data(exposure):
    """Load water treatment data for template"""
    treatment = HH_WaterTreatment.objects.filter(HHID=exposure).first()
    if treatment:
        return {
            'method': treatment.TREATMENT_TYPE,
            'other': treatment.TREATMENT_TYPE_OTHER or ''
        }
    return {'method': None, 'other': None}


def _load_animal_data(exposure):
    """Load animals data for template"""
    animal_data = {}
    
    animals = HH_Animal.objects.filter(HHID=exposure)
    for animal in animals:
        animal_type = animal.ANIMAL_TYPE
        animal_data[animal_type] = True
        if animal_type == 'other' and animal.ANIMAL_TYPE_OTHER:
            animal_data['other_text'] = animal.ANIMAL_TYPE_OTHER
    
    return animal_data


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
def household_exposure_create(request, hhid):
    """
    CREATE new exposure data for household
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 HOUSEHOLD EXPOSURE CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Check if exposure already exists
    if HH_Exposure.objects.filter(HHID=household).exists():
        logger.warning(f"⚠️ Exposure already exists for {hhid} - redirecting to update")
        messages.warning(
            request,
            f'Exposure data already exists for household {hhid}. Redirecting to update.'
        )
        return redirect('study_44en:household:exposure_update', hhid=hhid)
    
    # POST - Create new exposure
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
        exposure_form = HH_ExposureForm(request.POST)
        food_freq_form = HH_FoodFrequencyForm(request.POST)
        food_source_form = HH_FoodSourceForm(request.POST)
        
        if all([
            exposure_form.is_valid(),
            food_freq_form.is_valid(),
            food_source_form.is_valid()
        ]):
            try:
                with transaction.atomic():
                    logger.info("📝 Saving exposure data...")
                    
                    # 1. Save exposure
                    exposure = exposure_form.save(commit=False)
                    exposure.HHID = household
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"✅ Created exposure for {hhid}")
                    
                    # 2. Save water sources
                    _save_water_sources(request, exposure)
                    
                    # 3. Save water treatment
                    _save_water_treatment(request, exposure)
                    
                    # 4. Save animals
                    _save_animals(request, exposure)
                    
                    # 5. Save food frequency
                    food_freq = food_freq_form.save(commit=False)
                    food_freq.HHID = household
                    set_audit_metadata(food_freq, request.user)
                    food_freq.save()
                    logger.info("✅ Saved food frequency")
                    
                    # 6. Save food source
                    food_source = food_source_form.save(commit=False)
                    food_source.HHID = household
                    set_audit_metadata(food_source, request.user)
                    food_source.save()
                    logger.info("✅ Saved food source")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ EXPOSURE CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Created exposure data for household {hhid}'
                    )
                    return redirect('study_44en:household:detail', hhid=hhid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating exposure: {e}", exc_info=True)
                messages.error(request, f'Error creating exposure: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if exposure_form.errors:
                logger.error(f"Exposure form errors: {exposure_form.errors}")
            if food_freq_form.errors:
                logger.error(f"Food frequency errors: {food_freq_form.errors}")
            if food_source_form.errors:
                logger.error(f"Food source errors: {food_source_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        
        exposure_form = HH_ExposureForm()
        food_freq_form = HH_FoodFrequencyForm()
        food_source_form = HH_FoodSourceForm()
        logger.info("✅ Blank forms initialized")
    
    context = {
        'household': household,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': True,
        'is_readonly': False,
        'water_data': {},
        'treatment_method': None,
        'treatment_other': None,
        'animal_data': {},
    }
    
    logger.info("=" * 80)
    logger.info("=== 🌱 EXPOSURE CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_exposure_form.html',
        context
    )


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
def household_exposure_update(request, hhid):
    """
    UPDATE existing exposure data
    """
    logger.info("=" * 80)
    logger.info("=== 📝 HOUSEHOLD EXPOSURE UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get exposure (must exist for update)
    try:
        exposure = HH_Exposure.objects.get(HHID=household)
        logger.info(f"✅ Found existing exposure for {hhid}")
    except HH_Exposure.DoesNotExist:
        logger.warning(f"⚠️ No exposure found for {hhid} - redirecting to create")
        messages.error(
            request,
            f'No exposure data found for household {hhid}. Please create first.'
        )
        return redirect('study_44en:household:exposure_create', hhid=hhid)
    
    # Get food records (may or may not exist)
    try:
        food_freq = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_freq = None
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    # POST - Update exposure
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
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
                    logger.info("📝 Updating exposure data...")
                    
                    # 1. Update exposure
                    exposure = exposure_form.save(commit=False)
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"✅ Updated exposure for {hhid}")
                    
                    # 2. Update water sources (clear & recreate)
                    _save_water_sources(request, exposure)
                    
                    # 3. Update water treatment (clear & recreate)
                    _save_water_treatment(request, exposure)
                    
                    # 4. Update animals (clear & recreate)
                    _save_animals(request, exposure)
                    
                    # 5. Update food frequency
                    food_freq = food_freq_form.save(commit=False)
                    food_freq.HHID = household
                    set_audit_metadata(food_freq, request.user)
                    food_freq.save()
                    logger.info("✅ Updated food frequency")
                    
                    # 6. Update food source
                    food_source = food_source_form.save(commit=False)
                    food_source.HHID = household
                    set_audit_metadata(food_source, request.user)
                    food_source.save()
                    logger.info("✅ Updated food source")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ EXPOSURE UPDATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Updated exposure data for household {hhid}'
                    )
                    return redirect('study_44en:household:detail', hhid=hhid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating exposure: {e}", exc_info=True)
                messages.error(request, f'Error updating exposure: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if exposure_form.errors:
                logger.error(f"Exposure form errors: {exposure_form.errors}")
            if food_freq_form.errors:
                logger.error(f"Food frequency errors: {food_freq_form.errors}")
            if food_source_form.errors:
                logger.error(f"Food source errors: {food_source_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show form with existing data
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        exposure_form = HH_ExposureForm(instance=exposure)
        food_freq_form = HH_FoodFrequencyForm(instance=food_freq)
        food_source_form = HH_FoodSourceForm(instance=food_source)
        logger.info("✅ Forms initialized with existing data")
    
    # Load existing related data
    water_data = _load_water_data(exposure)
    treatment_data = _load_treatment_data(exposure)
    animal_data = _load_animal_data(exposure)
    
    context = {
        'household': household,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': False,
        'is_readonly': False,
        'water_data': water_data,
        'treatment_method': treatment_data['method'],
        'treatment_other': treatment_data['other'],
        'animal_data': animal_data,
    }
    
    logger.info("=" * 80)
    logger.info("=== 📝 EXPOSURE UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_exposure_form.html',
        context
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
def household_exposure_view(request, hhid):
    """
    VIEW exposure data (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== HHID HOUSEHOLD EXPOSURE VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get exposure (must exist)
    try:
        exposure = HH_Exposure.objects.get(HHID=household)
    except HH_Exposure.DoesNotExist:
        messages.error(request, f'No exposure data found for household {hhid}')
        return redirect('study_44en:household:detail', hhid=hhid)
    
    # Get food records
    try:
        food_freq = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_freq = None
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    # Create readonly forms
    exposure_form = HH_ExposureForm(instance=exposure)
    food_freq_form = HH_FoodFrequencyForm(instance=food_freq)
    food_source_form = HH_FoodSourceForm(instance=food_source)
    
    # Make all forms readonly
    make_form_readonly(exposure_form)
    make_form_readonly(food_freq_form)
    make_form_readonly(food_source_form)
    
    # Load existing data
    water_data = _load_water_data(exposure)
    treatment_data = _load_treatment_data(exposure)
    animal_data = _load_animal_data(exposure)
    
    context = {
        'household': household,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': False,
        'is_readonly': True,
        'water_data': water_data,
        'treatment_method': treatment_data['method'],
        'treatment_other': treatment_data['other'],
        'animal_data': animal_data,
    }
    
    logger.info("=" * 80)
    logger.info("=== HHID EXPOSURE VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_exposure_form.html',
        context
    )


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
def household_exposure(request, hhid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    
    This is kept for backward compatibility with old URLs
    """
    household, _ = get_household_with_related(request, hhid)
    
    # Check if exposure exists
    if HH_Exposure.objects.filter(HHID=household).exists():
        # Exists - redirect to update
        logger.info(f"🔄 Exposure exists for {hhid} - redirecting to update")
        return redirect('study_44en:household:exposure_update', hhid=hhid)
    else:
        # Not exists - redirect to create
        logger.info(f"🔄 No exposure for {hhid} - redirecting to create")
        return redirect('study_44en:household:exposure_create', hhid=hhid)


__all__ = [
    'household_exposure_create',
    'household_exposure_update',
    'household_exposure_view',
    'household_exposure',  # Deprecated but kept for compatibility
]