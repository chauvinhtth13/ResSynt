# backends/api/studies/study_44en/views/household/helpers.py
"""
Helper functions for household views - Following study_43en pattern
"""
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError

from backends.studies.study_44en.models.household import (
    HH_CASE,
    HH_Member,
    HH_Exposure,
)

logger = logging.getLogger(__name__)


# ==========================================
# AUDIT & METADATA
# ==========================================

def set_audit_metadata(instance, user):
    """Set audit fields on instance"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# DATA RETRIEVAL
# ==========================================

def get_household_with_related(request, hhid):
    """
    Get household with optimized queries and site filtering
    
    Args:
        request: HttpRequest object (for site filtering if needed)
        hhid: Household ID
        
    Returns:
        tuple: (household, members_queryset)
               
    Raises:
        Http404: If household not found
    """
    # For now, no site filtering for 44EN (can add later if needed)
    household = get_object_or_404(
        HH_CASE.objects.select_related(),
        HHID=hhid
    )
    
    # Get members (ordered by MEMBER_NUM)
    members = HH_Member.objects.filter(HHID=household).order_by('MEMBER_NUM')
    
    return household, members


def get_or_create_exposure(household):
    """Get or create exposure record (1-1 relationship)"""
    try:
        exposure = household.exposure
    except HH_Exposure.DoesNotExist:
        exposure = HH_Exposure(HHID=household)
    
    return exposure


# ==========================================
# SAVE OPERATIONS (Transaction-based)
# ==========================================

def save_household_and_related(
    request,
    household_form,
    member_formset,
    is_create=False
):
    """
    Save household with members in transaction
    
    Args:
        request: HttpRequest
        household_form: HH_CASEForm instance
        member_formset: HH_MemberFormSet instance
        is_create: bool, True if creating new household
        
    Returns:
        HH_CASE instance or None if error
    """
    try:
        with transaction.atomic():
            # 1. Save main household
            household = household_form.save(commit=False)
            set_audit_metadata(household, request.user)
            household.save()
            
            logger.info(f"{'Created' if is_create else 'Updated'} household: {household.HHID}")
            
            # 2. Save members
            if member_formset.is_valid():
                members = member_formset.save(commit=False)
                
                # Save new/updated members
                for member in members:
                    member.HHID = household
                    set_audit_metadata(member, request.user)
                    member.save()
                
                
                logger.info(f"Saved {len(members)} members for household {household.HHID}")
            else:
                logger.error(f"Member formset validation failed: {member_formset.errors}")
                return None
            
            return household
            
    except Exception as e:
        logger.error(f"Error saving household: {e}", exc_info=True)
        return None


# ==========================================
# FORM UTILITIES
# ==========================================

def make_form_readonly(form):
    """Make all form fields readonly"""
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': 'readonly',
            'disabled': 'disabled'
        })


def make_formset_readonly(formset):
    """Make all formset forms readonly"""
    for form in formset.forms:
        make_form_readonly(form)


def log_all_form_errors(forms_dict):
    """
    Log all validation errors from multiple forms
    
    Args:
        forms_dict: Dict with form names and form instances
        
    Returns:
        List of form names with errors
    """
    forms_with_errors = []
    
    for form_name, form in forms_dict.items():
        if hasattr(form, 'errors') and form.errors:
            logger.error(f"{form_name} errors: {form.errors}")
            forms_with_errors.append(form_name)
        
        # Check for non-form errors in formsets
        if hasattr(form, 'non_form_errors'):
            non_form_errs = form.non_form_errors()
            if non_form_errs:
                logger.error(f"{form_name} non-form errors: {non_form_errs}")
                forms_with_errors.append(form_name)
    
    return forms_with_errors
