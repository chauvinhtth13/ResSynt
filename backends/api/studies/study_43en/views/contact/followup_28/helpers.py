# backends/api/studies/study_43en/views/contact/followup_28/helpers.py
"""
Helper functions for Contact Follow-up Day 28 views.
"""
import logging
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError

from backends.studies.study_43en.models.contact import (
    ENR_CONTACT, FU_CONTACT_28, ContactMedicationHistory28,
)

# Use shared utilities
from backends.api.studies.study_43en.views.shared import (
    set_audit_metadata,
    make_form_readonly,
    make_formset_readonly,
    get_contact_case_chain,
)

logger = logging.getLogger(__name__)


def get_contact_followup28_with_related(request, usubjid):
    """
    Get contact follow-up 28 case with optimized queries.
    
    Returns:
        tuple: (enrollment_contact, followup_case or None)
    """
    enrollment, _ = get_contact_case_chain(request, usubjid)
    
    try:
        followup = FU_CONTACT_28.objects.select_related(
            'USUBJID'
        ).prefetch_related(
            'medications'
        ).get(USUBJID=enrollment)
        
        return enrollment, followup
    except FU_CONTACT_28.DoesNotExist:
        return enrollment, None


def save_contact_followup28_and_related(
    request,
    followup_form,
    medication_formset,
    enrollment_contact,
    is_create=False
):
    """
    Save contact follow-up 28 and related forms in transaction.
    
    Returns:
        FU_CONTACT_28 instance or None on error
    """
    try:
        with transaction.atomic():
            followup = followup_form.save(commit=False)
            
            if is_create:
                followup.USUBJID = enrollment_contact
            
            set_audit_metadata(followup, request.user)
            followup.save()
            
            logger.info(f"{'Created' if is_create else 'Updated'} contact follow-up Day 28: {followup.USUBJID.USUBJID}")
            
            _save_formset(medication_formset, followup, request.user, 'medications')
            
            return followup
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        messages.error(request, f'Lỗi validation: {e}')
        return None
    except Exception as e:
        logger.error(f"Error saving contact follow-up 28: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu thông tin theo dõi: {str(e)}')
        return None


def _save_formset(formset, parent_instance, user, name):
    """Generic helper to save formset with audit metadata."""
    instances = formset.save(commit=False)
    
    for instance in instances:
        instance.USUBJID = parent_instance
        set_audit_metadata(instance, user)
        instance.save()
    
    formset.save_m2m()
    logger.info(f"Saved {len(instances)} {name}")