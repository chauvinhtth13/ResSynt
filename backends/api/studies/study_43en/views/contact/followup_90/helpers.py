# backends/api/studies/study_43en/views/contact/followup_90/helpers.py
"""
Helper functions for Contact Follow-up Day 90 views.

Provides transaction handlers and validation utilities.
"""
import logging
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from backends.studies.study_43en.models.contact import (
    ENR_CONTACT, FU_CONTACT_90, ContactMedicationHistory90,
)
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params, get_site_filtered_object_or_404,
)

# Use shared utilities
from backends.api.studies.study_43en.views.shared import (
    set_audit_metadata,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


def get_contact_followup90_with_related(request, usubjid):
    """
    Get contact follow-up 90 case with optimized queries.
    
    Returns:
        tuple: (enrollment_contact, followup_case or None)
    """
    site_filter, filter_type = get_site_filter_params(request)
    enrollment_contact = get_site_filtered_object_or_404(
        ENR_CONTACT, site_filter, filter_type, USUBJID=usubjid
    )
    
    try:
        followup_case = FU_CONTACT_90.objects.select_related(
            'USUBJID'
        ).prefetch_related('medications').get(USUBJID=enrollment_contact)
        return enrollment_contact, followup_case
    except FU_CONTACT_90.DoesNotExist:
        return enrollment_contact, None


# ==========================================
# TRANSACTION HANDLER
# ==========================================

def save_contact_followup90_and_related(
    request,
    followup_form,
    medication_formset,
    enrollment_contact,
    is_create=False
):
    """
    Save contact follow-up 90 and all related forms in transaction
    
    Args:
        request: HttpRequest
        followup_form: ContactFollowUp90Form
        medication_formset: ContactMedicationHistory90FormSet
        enrollment_contact: ENR_CONTACT instance
        is_create: bool - True if creating new follow-up
    
    Returns:
        FU_CONTACT_90 instance or None on error
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
                f"{'Created' if is_create else 'Updated'} contact follow-up Day 90: "
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
        logger.error(f"Error saving contact follow-up 90: {e}", exc_info=True)
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
    logger.info(f"Saved {len(instances)} medications (Day 90)")


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
