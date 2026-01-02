# backends/api/studies/study_44en/views/household/views_household_food.py

"""
Household Food Views for Study 44EN
Handles food frequency and food source data

REFACTORED: Separated CREATE and UPDATE following household_case pattern
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.household import (
    HH_CASE, HH_FoodFrequency, HH_FoodSource
)
from backends.studies.study_44en.forms.household import (
    HH_FoodFrequencyForm, HH_FoodSourceForm
)
from .helpers import (
    get_household_with_related,
    set_audit_metadata,
    make_form_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
def household_food_create(request, hhid):
    """
    CREATE new food data for household
    """
    logger.info("=" * 80)
    logger.info("=== 🍽️ HOUSEHOLD FOOD CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Check if food data already exists
    freq_exists = HH_FoodFrequency.objects.filter(HHID=household).exists()
    source_exists = HH_FoodSource.objects.filter(HHID=household).exists()
    
    if freq_exists or source_exists:
        logger.warning(f"⚠️ Food data already exists for {hhid} - redirecting to update")
        messages.warning(
            request,
            f'Food data already exists for household {hhid}. Redirecting to update.'
        )
        return redirect('study_44en:household:food_update', hhid=hhid)
    
    # POST - Create new food data
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
        food_frequency_form = HH_FoodFrequencyForm(
            request.POST,
            prefix='frequency'
        )
        food_source_form = HH_FoodSourceForm(
            request.POST,
            prefix='source'
        )
        
        if food_frequency_form.is_valid() and food_source_form.is_valid():
            try:
                with transaction.atomic():
                    logger.info("📝 Saving food data...")
                    
                    # Save food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.HHID = household
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"✅ Created food frequency for {hhid}")
                    
                    # Save food source
                    food_source = food_source_form.save(commit=False)
                    food_source.HHID = household
                    set_audit_metadata(food_source, request.user)
                    food_source.save()
                    logger.info(f"✅ Created food source for {hhid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ FOOD CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Created food data for household {hhid}'
                    )
                    return redirect('study_44en:household:detail', hhid=hhid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating food data: {e}", exc_info=True)
                messages.error(request, f'Error creating food data: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if food_frequency_form.errors:
                logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            if food_source_form.errors:
                logger.error(f"Food source errors: {food_source_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        
        food_frequency_form = HH_FoodFrequencyForm(prefix='frequency')
        food_source_form = HH_FoodSourceForm(prefix='source')
        logger.info("✅ Blank forms initialized")
    
    context = {
        'household': household,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 🍽️ FOOD CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_food_form.html',
        context
    )


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
def household_food_update(request, hhid):
    """
    UPDATE existing food data
    """
    logger.info("=" * 80)
    logger.info("=== 📝 HOUSEHOLD FOOD UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get food frequency (must exist for update)
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
        logger.info(f"✅ Found food frequency for {hhid}")
    except HH_FoodFrequency.DoesNotExist:
        logger.warning(f"⚠️ No food frequency found for {hhid}")
        food_frequency = None
    
    # Get food source (must exist for update)
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
        logger.info(f"✅ Found food source for {hhid}")
    except HH_FoodSource.DoesNotExist:
        logger.warning(f"⚠️ No food source found for {hhid}")
        food_source = None
    
    # If neither exists, redirect to create
    if food_frequency is None and food_source is None:
        logger.warning(f"⚠️ No food data found for {hhid} - redirecting to create")
        messages.error(
            request,
            f'No food data found for household {hhid}. Please create first.'
        )
        return redirect('study_44en:household:food_create', hhid=hhid)
    
    # POST - Update food data
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
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
                    logger.info("📝 Updating food data...")
                    
                    # Update food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.HHID = household
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"✅ Updated food frequency for {hhid}")
                    
                    # Update food source
                    food_source = food_source_form.save(commit=False)
                    food_source.HHID = household
                    set_audit_metadata(food_source, request.user)
                    food_source.save()
                    logger.info(f"✅ Updated food source for {hhid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ FOOD UPDATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Updated food data for household {hhid}'
                    )
                    return redirect('study_44en:household:detail', hhid=hhid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating food data: {e}", exc_info=True)
                messages.error(request, f'Error updating food data: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if food_frequency_form.errors:
                logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            if food_source_form.errors:
                logger.error(f"Food source errors: {food_source_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show form with existing data
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        food_frequency_form = HH_FoodFrequencyForm(
            instance=food_frequency,
            prefix='frequency'
        )
        food_source_form = HH_FoodSourceForm(
            instance=food_source,
            prefix='source'
        )
        logger.info("✅ Forms initialized with existing data")
    
    context = {
        'household': household,
        'food_frequency': food_frequency,
        'food_source': food_source,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'is_create': False,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 📝 FOOD UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_food_form.html',
        context
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
def household_food_view(request, hhid):
    """
    VIEW food data (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== HHID HOUSEHOLD FOOD VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get food frequency
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_frequency = None
    
    # Get food source
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    # If neither exists, redirect to detail
    if food_frequency is None and food_source is None:
        messages.error(request, f'No food data found for household {hhid}')
        return redirect('study_44en:household:detail', hhid=hhid)
    
    # Create readonly forms
    food_frequency_form = HH_FoodFrequencyForm(
        instance=food_frequency,
        prefix='frequency'
    )
    food_source_form = HH_FoodSourceForm(
        instance=food_source,
        prefix='source'
    )
    
    # Make all forms readonly
    make_form_readonly(food_frequency_form)
    make_form_readonly(food_source_form)
    
    context = {
        'household': household,
        'food_frequency': food_frequency,
        'food_source': food_source,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("=" * 80)
    logger.info("=== HHID FOOD VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_food_form.html',
        context
    )


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
def household_food(request, hhid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    
    This is kept for backward compatibility with old URLs
    """
    household, _ = get_household_with_related(request, hhid)
    
    # Check if food data exists
    freq_exists = HH_FoodFrequency.objects.filter(HHID=household).exists()
    source_exists = HH_FoodSource.objects.filter(HHID=household).exists()
    
    if freq_exists or source_exists:
        # Data exists - redirect to update
        logger.info(f"🔄 Food data exists for {hhid} - redirecting to update")
        return redirect('study_44en:household:food_update', hhid=hhid)
    else:
        # No data - redirect to create
        logger.info(f"🔄 No food data for {hhid} - redirecting to create")
        return redirect('study_44en:household:food_create', hhid=hhid)


__all__ = [
    'household_food_create',
    'household_food_update',
    'household_food_view',
    'household_food',  # Deprecated but kept for compatibility
]