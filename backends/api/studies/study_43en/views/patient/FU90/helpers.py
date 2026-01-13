
# Site filtering utilities
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
)

# backends/studies/study_43en/views/patient/FU90/helpers.py
"""
Helper functions for Follow-up Day 90 views

Shared utilities for audit logging, data retrieval, and form processing
"""
import logging
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
    FU_CASE_90,
    Rehospitalization90,
    FollowUpAntibiotic90,
)

logger = logging.getLogger(__name__)


# ==========================================
# AUDIT & METADATA
# ==========================================

def set_audit_metadata(instance, user):
    """
    Set audit fields on instance
    
    Args:
        instance: Model instance with audit fields
        user: User object
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# DATA RETRIEVAL
# ==========================================

def get_followup90_with_related(request, usubjid):
    """
    Get follow-up 90 case with optimized queries
    
    Args:
        usubjid: Patient USUBJID
    
    Returns:
        tuple: (screening_case, enrollment_case, followup_case90 or None)
    """
    # Get site filtering parameters
    site_filter, filter_type = get_site_filter_params(request)

    #  Get with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE,
        site_filter,
        filter_type,
        USUBJID=usubjid
    )
    #  Get with site filtering
    enrollment_case = get_site_filtered_object_or_404(
        ENR_CASE,
        site_filter,
        filter_type,
        USUBJID=screening_case
    )
    
    try:
        followup_case90 = FU_CASE_90.objects.select_related(
            'USUBJID',
            'USUBJID__USUBJID'
        ).prefetch_related(
            'rehospitalizations',
            'antibiotics'
        ).get(USUBJID=enrollment_case)
        
        return screening_case, enrollment_case, followup_case90
    except FU_CASE_90.DoesNotExist:
        return screening_case, enrollment_case, None


# ==========================================
# FORM UTILITIES
# ==========================================

def make_form_readonly(form):
    """Make all form fields readonly"""
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': True,
            'disabled': True
        })


def make_formset_readonly(formset):
    """Make all formset fields readonly"""
    for form in formset.forms:
        make_form_readonly(form)


# ==========================================
# TRANSACTION HANDLER
# ==========================================

def save_followup90_and_related(
    request,
    followup_form,
    rehospitalization_formset,
    antibiotic_formset,
    enrollment_case,
    is_create=False
):
    """
    Save follow-up 90 and all related forms in transaction
    
    Args:
        request: HttpRequest
        followup_form: FollowUpCase90Form
        rehospitalization_formset: Rehospitalization90FormSet
        antibiotic_formset: FollowUpAntibiotic90FormSet
        enrollment_case: ENR_CASE instance
        is_create: bool - True if creating new follow-up
    
    Returns:
        FU_CASE_90 instance or None on error
    """
    try:
        with transaction.atomic():
            # 1. Save follow-up case (main)
            followup = followup_form.save(commit=False)
            
            if is_create:
                followup.USUBJID = enrollment_case
            
            set_audit_metadata(followup, request.user)
            followup.save()
            
            logger.info(
                f"{'Created' if is_create else 'Updated'} follow-up Day 90: "
                f"{followup.USUBJID.USUBJID.USUBJID}"
            )
            
            # 2. Save rehospitalizations
            _save_rehospitalization_formset(rehospitalization_formset, followup, request.user)
            
            # 3. Save antibiotics
            _save_antibiotic_formset(antibiotic_formset, followup, request.user)
            
            return followup
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        messages.error(request, f'Lỗi validation: {e}')
        return None
        
    except Exception as e:
        logger.error(f"Error saving follow-up 90: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu thông tin theo dõi: {str(e)}')
        return None


def _save_rehospitalization_formset(formset, followup_case, user):
    """Helper to save rehospitalization formset"""
    instances = formset.save(commit=False)
    
    for instance in instances:
        instance.USUBJID = followup_case
        set_audit_metadata(instance, user)
        instance.save()
    

    
    formset.save_m2m()
    logger.info(f"Saved {len(instances)} rehospitalizations (Day 90)")


def _save_antibiotic_formset(formset, followup_case, user):
    """Helper to save antibiotic formset"""
    instances = formset.save(commit=False)
    
    for instance in instances:
        instance.USUBJID = followup_case
        set_audit_metadata(instance, user)
        instance.save()
    

    
    formset.save_m2m()
    logger.info(f"Saved {len(instances)} antibiotics (Day 90)")


# ==========================================
# VALIDATION HELPERS
# ==========================================

def log_form_errors(form, form_name):
    """Log form validation errors"""
    if form.errors:
        logger.warning(f"{form_name} errors: {form.errors}")
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
