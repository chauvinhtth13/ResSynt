# backends/api/studies/study_44en/views/household/food_helpers.py
"""
Household Food Helper Functions

Shared utilities for household food CRUD views.
Following Django development rules: Backend-first approach.
"""

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib import messages

from backends.studies.study_44en.models.household import (
    HH_CASE,
    HH_FoodFrequency,
    HH_FoodSource,
)

logger = logging.getLogger(__name__)


# ==========================================
# AUDIT METADATA (TODO: Move to centralized helpers)
# ==========================================

def set_audit_metadata(instance, user):
    """
    Set audit fields on instance
    
     TODO: Move to backends/audit_log/utils/view_helpers.py
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# READ-ONLY HELPERS (TODO: Move to centralized helpers)
# ==========================================

def make_form_readonly(form):
    """
    Make all form fields readonly
    
     TODO: Move to backends/audit_log/utils/view_helpers.py
    """
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': True,
            'disabled': True
        })


# ==========================================
# DATA RETRIEVAL
# ==========================================

def get_household_with_food(request, hhid):
    """
    Get household with food data
    
    Returns:
        tuple: (household, food_frequency, food_source)
        
    Note:
        - Returns (household, None, None) if food data doesn't exist
    """
    logger.info(f"📥 Fetching household {hhid} with food data...")
    
    # Get household (with 404 if not found)
    household = get_object_or_404(HH_CASE, HHID=hhid)
    logger.info(f"   Found household: {household.HHID}")
    
    # Get food frequency
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
        logger.info(f"   Found food frequency")
    except HH_FoodFrequency.DoesNotExist:
        logger.info(f"   No food frequency found")
        food_frequency = None
    
    # Get food source
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
        logger.info(f"   Found food source")
    except HH_FoodSource.DoesNotExist:
        logger.info(f"   No food source found")
        food_source = None
    
    return household, food_frequency, food_source


# ==========================================
# TRANSACTION HANDLER
# ==========================================

def save_food_data(request, forms_dict, household, is_create=False):
    """
    Save food frequency and food source in transaction
    
    COMPATIBLE with Universal Audit System standard structure
    
    Args:
        request: HttpRequest
        forms_dict: Standard forms_dict from Universal Audit System
            {
                'main': HH_FoodFrequencyForm,
                'related': {
                    'food_source': HH_FoodSourceForm
                }
            }
        household: HH_CASE instance
        is_create: bool - True if creating new food data
    
    Returns:
        HH_FoodFrequency instance or None on error
    """
    logger.info("="*80)
    logger.info(f"💾 SAVING FOOD DATA (is_create={is_create})")
    logger.info("="*80)
    
    try:
        with transaction.atomic(using='db_study_44en'):
            # ===================================
            # 1. SAVE FOOD FREQUENCY (MAIN)
            # ===================================
            logger.info(" Step 1: Saving food frequency...")
            
            food_frequency = forms_dict['main'].save(commit=False)
            food_frequency.HHID = household
            
            set_audit_metadata(food_frequency, request.user)
            
            if is_create and hasattr(food_frequency, 'version'):
                food_frequency.version = 0
            
            food_frequency.save()
            
            logger.info(f"   Saved food frequency for HHID={household.HHID}")
            
            # ===================================
            # 2. SAVE FOOD SOURCE (RELATED)
            # ===================================
            if 'related' in forms_dict and 'food_source' in forms_dict['related']:
                logger.info(" Step 2: Saving food source...")
                
                food_source = forms_dict['related']['food_source'].save(commit=False)
                food_source.HHID = household
                set_audit_metadata(food_source, request.user)
                food_source.save()
                
                logger.info(f"   Saved food source for HHID={household.HHID}")
            
            logger.info("="*80)
            logger.info(f"SAVE COMPLETE - Food data for {household.HHID}")
            logger.info("="*80)
            
            return food_frequency
            
    except Exception as e:
        logger.error("="*80)
        logger.error(f" SAVE FAILED: {e}")
        logger.error("="*80)
        logger.error(f"Full error:", exc_info=True)
        messages.error(request, f'Lỗi khi lưu: {str(e)}')
        return None


# ==========================================
# VALIDATION HELPERS
# ==========================================

def log_form_errors(form, form_name):
    """Log form validation errors"""
    if form.errors:
        logger.warning(f" {form_name} errors: {form.errors}")
        return True
    return False


def log_all_form_errors(forms_dict):
    """
    Log all form validation errors
    
    Args:
        forms_dict: Dict of {form_name: form_instance}
    
    Returns:
        list: Names of forms with errors
    """
    forms_with_errors = []
    
    for name, form in forms_dict.items():
        if log_form_errors(form, name):
            forms_with_errors.append(name)
    
    return forms_with_errors


# ==========================================
# BUSINESS LOGIC HELPERS
# ==========================================

def check_food_data_exists(household):
    """
    Check if food data exists for household
    
    Returns:
        tuple: (freq_exists, source_exists)
    """
    freq_exists = HH_FoodFrequency.objects.filter(HHID=household).exists()
    source_exists = HH_FoodSource.objects.filter(HHID=household).exists()
    
    return freq_exists, source_exists


def get_food_summary(household):
    """
    Get summary statistics for food data
    
    Returns:
        dict: Summary data
    """
    try:
        food_frequency = HH_FoodFrequency.objects.get(HHID=household)
        has_frequency = True
    except HH_FoodFrequency.DoesNotExist:
        has_frequency = False
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
        has_source = True
    except HH_FoodSource.DoesNotExist:
        has_source = False
    
    return {
        'has_frequency': has_frequency,
        'has_source': has_source,
        'is_complete': has_frequency and has_source,
    }
