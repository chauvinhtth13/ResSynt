# backends/api/studies/study_44en/views/household/views_household_food.py
"""
✅ REFACTORED: Household Food Views - Using Universal Audit System

Following Django development rules:
- Backend-first approach
- Universal Audit System (Tier 2 - Multi-Form, no formsets)
- Handles 2 related forms: FoodFrequency + FoodSource
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import models
from backends.studies.study_44en.models.household import (
    HH_CASE,
    HH_FoodFrequency,
    HH_FoodSource
)

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_FoodFrequencyForm,
    HH_FoodSourceForm
)

# ✅ Import Universal Audit System
from backends.audit_log.utils.decorators import audit_log
from backends.audit_log.utils.processors import process_crf_update

# Import permission decorators
from backends.studies.study_44en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
)

# Import helpers
from .helpers import (
    get_household_with_related,
    set_audit_metadata,
    make_form_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS (Backend Logic)
# ==========================================

def save_food_data(request, forms_dict, household, is_create=False):
    """
    ✅ Backend save logic for food frequency + food source
    
    Args:
        request: HttpRequest
        forms_dict: Dictionary containing validated forms
            - 'main': HH_FoodFrequencyForm
            - 'related': {'food_source': HH_FoodSourceForm}
        household: HH_CASE instance
        is_create: Boolean flag
    
    Returns:
        HH_FoodFrequency instance
    """
    logger.info(f"💾 Saving food data (is_create={is_create})")
    
    with transaction.atomic(using='db_study_44en'):
        # 1. Save food frequency (main)
        food_frequency = forms_dict['main'].save(commit=False)
        food_frequency.HHID = household
        set_audit_metadata(food_frequency, request.user)
        
        if is_create and hasattr(food_frequency, 'version'):
            food_frequency.version = 0
        
        food_frequency.save()
        logger.info(f"✅ Saved food frequency for HHID={household.HHID}")
        
        # 2. Save food source (related)
        if 'related' in forms_dict and 'food_source' in forms_dict['related']:
            food_source = forms_dict['related']['food_source'].save(commit=False)
            food_source.HHID = household
            set_audit_metadata(food_source, request.user)
            food_source.save()
            logger.info(f"✅ Saved food source for HHID={household.HHID}")
        
        return food_frequency


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('hh_foodfrequency')
def household_food_create(request, hhid):
    """
    ✅ Create new food data for household
    
    Following rules:
    - Django Forms handle validation (backend)
    - NO audit needed for CREATE
    - Save 2 forms in transaction
    """
    logger.info("="*80)
    logger.info("=== 🍽️ HOUSEHOLD FOOD CREATE START ===")
    logger.info("="*80)
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Check if food data already exists
    freq_exists = HH_FoodFrequency.objects.filter(HHID=household).exists()
    source_exists = HH_FoodSource.objects.filter(HHID=household).exists()
    
    if freq_exists or source_exists:
        logger.warning(f"⚠️ Food data already exists for {hhid}")
        messages.warning(
            request,
            f'Food data already exists for {hhid}. Redirecting to update.'
        )
        return redirect('study_44en:household:food_update', hhid=hhid)
    
    # GET - Show blank forms
    if request.method == 'GET':
        food_frequency_form = HH_FoodFrequencyForm(prefix='frequency')
        food_source_form = HH_FoodSourceForm(prefix='source')
        
        context = {
            'household': household,
            'food_frequency_form': food_frequency_form,
            'food_source_form': food_source_form,
            'is_create': True,
            'is_readonly': False,
        }
        
        logger.info("📄 Showing blank forms")
        return render(
            request,
            'studies/study_44en/CRF/household/household_food_form.html',
            context
        )
    
    # POST - Create food data
    food_frequency_form = HH_FoodFrequencyForm(
        request.POST,
        prefix='frequency'
    )
    food_source_form = HH_FoodSourceForm(
        request.POST,
        prefix='source'
    )
    
    # ✅ Backend validation (Django Forms)
    if food_frequency_form.is_valid() and food_source_form.is_valid():
        try:
            # ✅ Use helper to save in transaction
            forms_dict = {
                'main': food_frequency_form,
                'related': {
                    'food_source': food_source_form
                }
            }
            
            food_frequency = save_food_data(
                request,
                forms_dict,
                household,
                is_create=True
            )
            
            logger.info("="*80)
            logger.info(f"=== ✅ FOOD CREATE SUCCESS: {hhid} ===")
            logger.info("="*80)
            
            messages.success(
                request,
                f'Tạo mới food data cho hộ {hhid} thành công!'
            )
            return redirect('study_44en:household:detail', hhid=hhid)
            
        except Exception as e:
            logger.error(f"❌ Create failed: {e}", exc_info=True)
            messages.error(request, f'Lỗi khi tạo: {str(e)}')
    else:
        # Log validation errors
        logger.error("❌ Form validation failed")
        if food_frequency_form.errors:
            logger.error(f"Food frequency errors: {food_frequency_form.errors}")
        if food_source_form.errors:
            logger.error(f"Food source errors: {food_source_form.errors}")
        
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # Re-render with errors
    context = {
        'household': household,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'is_create': True,
        'is_readonly': False,
    }
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_food_form.html',
        context
    )


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('hh_foodfrequency')
@audit_log(model_name='HH_FOODFREQUENCY', get_patient_id_from='hhid')
def household_food_update(request, hhid):
    """
    ✅ Update food data WITH UNIVERSAL AUDIT SYSTEM (Tier 2)
    
    Following rules:
    - Use Universal Audit System for change tracking
    - Handles 2 related forms automatically
    - Backend handles all logic
    """
    logger.info("="*80)
    logger.info(f"=== 📝 HOUSEHOLD FOOD UPDATE START ===")
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    logger.info("="*80)
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get food frequency (must exist for update)
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
        logger.info(f"Found food frequency for {hhid}")
    except HH_FoodFrequency.DoesNotExist:
        logger.warning(f"⚠️ No food frequency found for {hhid}")
        food_frequency = None
    
    # Get food source (must exist for update)
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
        logger.info(f"Found food source for {hhid}")
    except HH_FoodSource.DoesNotExist:
        logger.warning(f"⚠️ No food source found for {hhid}")
        food_source = None
    
    # If neither exists, redirect to create
    if food_frequency is None and food_source is None:
        logger.warning(f"⚠️ No food data found for {hhid}")
        messages.error(
            request,
            f'No food data found for {hhid}. Please create first.'
        )
        return redirect('study_44en:household:food_create', hhid=hhid)
    
    # GET - Show current data
    if request.method == 'GET':
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
            'food_frequency': food_frequency,
            'food_source': food_source,
            'food_frequency_form': food_frequency_form,
            'food_source_form': food_source_form,
            'is_create': False,
            'is_readonly': False,
            'current_version': getattr(food_frequency, 'version', 0),
        }
        
        logger.info(f"📄 Showing form for HHID={hhid}")
        return render(
            request,
            'studies/study_44en/CRF/household/household_food_form.html',
            context
        )
    
    # ✅ POST - USE UNIVERSAL AUDIT SYSTEM (Tier 2)
    logger.info("🔄 Using Universal Audit System (Tier 2 - Multi-Form)")
    
    # ✅ Configure forms for Universal Audit
    forms_config = {
        'main': {
            'class': HH_FoodFrequencyForm,
            'instance': food_frequency,
            'prefix': 'frequency'
        },
        'related': {
            'food_source': {
                'class': HH_FoodSourceForm,
                'instance': food_source,
                'prefix': 'source'
            }
        }
    }
    
    # ✅ Define save callback
    def save_callback(request, forms_dict):
        return save_food_data(
            request,
            forms_dict,
            household,
            is_create=False
        )
    
    # ✅ Use Universal Audit System
    return process_crf_update(
        request=request,
        instance=food_frequency,
        form_class=None,  # Using forms_config instead
        template_name='studies/study_44en/CRF/household/household_food_form.html',
        redirect_url=reverse('study_44en:household:detail', kwargs={'hhid': hhid}),
        extra_context={
            'household': household,
            'food_frequency': food_frequency,
            'food_source': food_source,
            'is_create': False,
        },
        forms_config=forms_config,
        save_callback=save_callback,
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('hh_foodfrequency')
def household_food_view(request, hhid):
    """
    ✅ View food data (read-only)
    
    Following rules:
    - Use template logic to make readonly
    - No JavaScript needed
    """
    logger.info(f"👁️ Read-only view for food {hhid}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get food data
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_frequency = None
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    # If neither exists, redirect to detail
    if food_frequency is None and food_source is None:
        messages.error(request, f'No food data found for {hhid}')
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
    
    # ✅ Make all forms readonly (backend logic)
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
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_food_form.html',
        context
    )


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
@require_crf_view('hh_foodfrequency')
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
        logger.info(f"📄 Food data exists for {hhid} - redirecting to update")
        return redirect('study_44en:household:food_update', hhid=hhid)
    else:
        # No data - redirect to create
        logger.info(f"📄 No food data for {hhid} - redirecting to create")
        return redirect('study_44en:household:food_create', hhid=hhid)


__all__ = [
    'household_food_create',
    'household_food_update',
    'household_food_view',
    'household_food',  # Deprecated but kept for compatibility
]