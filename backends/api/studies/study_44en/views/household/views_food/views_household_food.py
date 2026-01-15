# backends/api/studies/study_44en/views/household/views_household_food.py
"""
REFACTORED: Household Food Views - Using Separate Helpers + Universal Audit

Following Django development rules:
- Backend-first approach
- Helpers separated into food_helpers.py
- Universal Audit System (Tier 2 - Multi-Form, no formsets)

Architecture:
- Main form: HH_FoodFrequency
- Related form: HH_FoodSource (1-to-1 with HH_CASE)
"""

import logging
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
from backends.studies.study_44en.models import AuditLog, AuditLogDetail

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_FoodFrequencyForm,
    HH_FoodSourceForm
)

# Import Universal Audit System
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import process_crf_update

# Import permission decorators
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
)

# Import helpers from separate file
from .food_helpers import (
    get_household_with_food,
    save_food_data,
    check_food_data_exists,
    get_food_summary,
    make_form_readonly,
    log_all_form_errors,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW (NO AUDIT)
# ==========================================

@login_required
@require_crf_add('hh_foodfrequency')
def household_food_create(request, hhid):
    """
    Create new food data for household
    
    Following rules:
    - Django Forms handle validation (backend)
    - NO audit needed for CREATE
    - Save 2 forms in transaction using helper
    
    Workflow:
    1. GET: Show blank food frequency + food source forms
    2. POST: Validate all forms → Save in transaction → Redirect
    """
    logger.info("="*80)
    logger.info("=== 🍽️ HOUSEHOLD FOOD CREATE START ===")
    logger.info("="*80)
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Use helper to get household and check existing data
    household, food_frequency, food_source = get_household_with_food(request, hhid)
    
    # Check if food data already exists
    if food_frequency or food_source:
        logger.warning(f"⚠️ Food data already exists for {hhid}")
        messages.warning(
            request,
            f'Food data already exists for {hhid}. Redirecting to update.'
        )
        return redirect('study_44en:household:food_update', hhid=hhid)
    
    # GET - Show blank forms
    if request.method == 'GET':
        logger.info("📄 GET REQUEST - Showing blank forms...")
        
        food_frequency_form = HH_FoodFrequencyForm(prefix='frequency')
        food_source_form = HH_FoodSourceForm(prefix='source')
        
        logger.info("   Blank forms initialized")
        
        context = {
            'household': household,
            'food_frequency_form': food_frequency_form,
            'food_source_form': food_source_form,
            'is_create': True,
            'is_readonly': False,
        }
        
        logger.info("="*80)
        logger.info("=== 🍽️ FOOD CREATE END (GET) - Rendering template ===")
        logger.info("="*80)
        
        return render(
            request,
            'studies/study_44en/CRF/household/household_food_form.html',
            context
        )
    
    # POST - Create food data
    logger.info("📨 POST REQUEST - Processing form submission...")
    
    food_frequency_form = HH_FoodFrequencyForm(
        request.POST,
        prefix='frequency'
    )
    food_source_form = HH_FoodSourceForm(
        request.POST,
        prefix='source'
    )
    
    logger.info(" Validating forms...")
    
    # Backend validation (Django Forms)
    freq_valid = food_frequency_form.is_valid()
    source_valid = food_source_form.is_valid()
    
    logger.info(f"   Food frequency: {'VALID ' if freq_valid else 'INVALID '}")
    logger.info(f"   Food source: {'VALID ' if source_valid else 'INVALID '}")
    
    if freq_valid and source_valid:
        logger.info("💾 All forms valid - Calling save helper...")
        
        # Prepare forms_dict for save helper
        forms_dict = {
            'main': food_frequency_form,
            'related': {
                'food_source': food_source_form
            }
        }
        
        # Use helper to save in transaction
        food_frequency = save_food_data(
            request,
            forms_dict,
            household,
            is_create=True
        )
        
        if food_frequency:
            logger.info("="*80)
            logger.info(f"=== FOOD CREATE SUCCESS: {hhid} ===")
            logger.info("="*80)
            
            messages.success(
                request,
                f'Tạo mới food data cho hộ {hhid} thành công!'
            )
            return redirect('study_44en:household:detail', hhid=hhid)
        else:
            logger.error(" Save helper returned None")
            messages.error(request, 'Lỗi khi lưu dữ liệu. Vui lòng thử lại.')
    else:
        # Use helper to log errors
        forms_with_errors = log_all_form_errors({
            'Food Frequency Form': food_frequency_form,
            'Food Source Form': food_source_form,
        })
        
        if forms_with_errors:
            error_msg = f' Vui lòng kiểm tra lại: {", ".join(forms_with_errors)}'
            messages.error(request, error_msg)
    
    # Re-render with errors
    context = {
        'household': household,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("="*80)
    logger.info("=== 🍽️ FOOD CREATE END (POST) - Rendering with errors ===")
    logger.info("="*80)
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_food_form.html',
        context
    )


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT - TIER 2)
# ==========================================

@login_required
@require_crf_change('hh_foodfrequency')
@audit_log(
    model_name='HH_FOODFREQUENCY',
    get_patient_id_from='hhid',
    patient_model=HH_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def household_food_update(request, hhid):
    """
    Update food data WITH UNIVERSAL AUDIT SYSTEM (Tier 2)
    
    Following rules:
    - Use Universal Audit System for change tracking
    - Handles 2 related forms automatically
    - Backend handles all logic
    - Helpers handle save logic
    """
    logger.info("="*80)
    logger.info(f"===  HOUSEHOLD FOOD UPDATE START ===")
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    logger.info("="*80)
    
    # Use helper to get household and food data
    household, food_frequency, food_source = get_household_with_food(request, hhid)
    
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
        logger.info("="*80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("="*80)
        
        food_frequency_form = HH_FoodFrequencyForm(
            instance=food_frequency,
            prefix='frequency'
        )
        food_source_form = HH_FoodSourceForm(
            instance=food_source,
            prefix='source'
        )
        
        logger.info(f"   Forms initialized with existing data")
        
        # Use helper to get summary
        summary = get_food_summary(household)
        
        context = {
            'household': household,
            'food_frequency': food_frequency,
            'food_source': food_source,
            'food_frequency_form': food_frequency_form,
            'food_source_form': food_source_form,
            'summary': summary,
            'is_create': False,
            'is_readonly': False,
            'current_version': getattr(food_frequency, 'version', 0),
        }
        
        logger.info("="*80)
        logger.info(f"===  FOOD UPDATE END (GET) - Rendering template ===")
        logger.info("="*80)
        
        return render(
            request,
            'studies/study_44en/CRF/household/household_food_form.html',
            context
        )
    
    # POST - USE UNIVERSAL AUDIT SYSTEM (Tier 2)
    logger.info("="*80)
    logger.info("Using Universal Audit System (Tier 2 - Multi-Form)")
    logger.info("="*80)
    
    # Configure forms for Universal Audit
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
    
    # Define save callback using helper
    def save_callback(request, forms_dict):
        """Save callback - uses helper function"""
        return save_food_data(
            request,
            forms_dict,
            household,
            is_create=False
        )
    
    # Use Universal Audit System
    logger.info("🚀 Calling process_crf_update...")
    
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
            'summary': get_food_summary(household),
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
    View food data (read-only)
    
    Following rules:
    - Use backend logic to make readonly
    - No JavaScript needed
    """
    logger.info("="*80)
    logger.info(f"=== 👁️ HOUSEHOLD FOOD VIEW (READ-ONLY): {hhid} ===")
    logger.info("="*80)
    
    # Use helper to get household and food data
    household, food_frequency, food_source = get_household_with_food(request, hhid)
    
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
    
    # Use helper to make all forms readonly
    make_form_readonly(food_frequency_form)
    make_form_readonly(food_source_form)
    
    logger.info(f"   Forms made readonly")
    
    # Use helper to get summary
    summary = get_food_summary(household)
    
    context = {
        'household': household,
        'food_frequency': food_frequency,
        'food_source': food_source,
        'food_frequency_form': food_frequency_form,
        'food_source_form': food_source_form,
        'summary': summary,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("="*80)
    logger.info("=== 👁️ FOOD VIEW END - Rendering template ===")
    logger.info("="*80)
    
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
    # Use helper to check if food data exists
    household, food_frequency, food_source = get_household_with_food(request, hhid)
    
    if food_frequency or food_source:
        # Data exists - redirect to update
        logger.info(f"📄 Food data exists for {hhid} - redirecting to update")
        return redirect('study_44en:household:food_update', hhid=hhid)
    else:
        # No data - redirect to create
        logger.info(f"📄 No food data for {hhid} - redirecting to create")
        return redirect('study_44en:household:food_create', hhid=hhid)


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'household_food_create',
    'household_food_update',
    'household_food_view',
    'household_food',  # Deprecated but kept for compatibility
]
