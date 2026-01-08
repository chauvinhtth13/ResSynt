
# Site filtering utilities
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
)

# backends/studies/study_43en/views/contact/FU28/helpers.py
"""
Helper functions for Contact Follow-up Day 28 views

Shared utilities for audit logging, data retrieval, and form processing
"""
import logging
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from backends.studies.study_43en.models.contact import (
    ENR_CONTACT,
    FU_CONTACT_28,
    ContactMedicationHistory28,
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

def get_contact_followup28_with_related(request, usubjid):
    """
    Get contact follow-up 28 case with optimized queries
    
    Args:
        usubjid: Contact USUBJID
    
    Returns:
        tuple: (enrollment_contact, followup_case or None)
    """
    # Get site filtering parameters
    site_filter, filter_type = get_site_filter_params(request)

    #  Get with site filtering
    enrollment_contact = get_site_filtered_object_or_404(
        ENR_CONTACT,
        site_filter,
        filter_type,
        USUBJID=usubjid
    )
    
    try:
        followup_case = FU_CONTACT_28.objects.select_related(
            'USUBJID'
        ).prefetch_related(
            'medications'
        ).get(USUBJID=enrollment_contact)
        
        return enrollment_contact, followup_case
    except FU_CONTACT_28.DoesNotExist:
        return enrollment_contact, None


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

def save_contact_followup28_and_related(
    request,
    followup_form,
    medication_formset,
    enrollment_contact,
    is_create=False
):
    """
    Save contact follow-up 28 and all related forms in transaction
    
    Args:
        request: HttpRequest
        followup_form: ContactFollowUp28Form
        medication_formset: ContactMedicationHistory28FormSet
        enrollment_contact: ENR_CONTACT instance
        is_create: bool - True if creating new follow-up
    
    Returns:
        FU_CONTACT_28 instance or None on error
    """
    try:
        with transaction.atomic():
            # 1. Save follow-up case (main)
            followup = followup_form.save(commit=False)
            
            if is_create:
                followup.USUBJID = enrollment_contact
            
            set_audit_metadata(followup, request.user)
            followup.save()
            
            logger.info(
                f"{'Created' if is_create else 'Updated'} contact follow-up Day 28: "
                f"{followup.USUBJID.USUBJID}"
            )
            
            # 2. Save medications
            _save_medication_formset(medication_formset, followup, request.user)
            
            return followup
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        messages.error(request, f'Lỗi validation: {e}')
        return None
        
    except Exception as e:
        logger.error(f"Error saving contact follow-up 28: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu thông tin theo dõi: {str(e)}')
        return None


def _save_medication_formset(formset, followup_case, user):
    """Helper to save medication formset"""
    instances = formset.save(commit=False)
    
    for instance in instances:
        instance.USUBJID = followup_case
        set_audit_metadata(instance, user)
        instance.save()
    

    
    formset.save_m2m()
    logger.info(f"Saved {len(instances)} medications")


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