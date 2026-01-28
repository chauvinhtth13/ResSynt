# backends/api/studies/study_43en/views/patient/followup_28/helpers.py
"""
Helper functions for Follow-up Day 28 views.
"""
import logging
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError

from backends.studies.study_43en.models.patient import (
    SCR_CASE, ENR_CASE, FU_CASE_28,
    Rehospitalization, FollowUpAntibiotic,
)

# Use shared utilities
from backends.api.studies.study_43en.views.shared import (
    set_audit_metadata,
    make_form_readonly,
    make_formset_readonly,
    get_patient_case_chain,
)

logger = logging.getLogger(__name__)


def get_followup_with_related(request, usubjid):
    """
    Get follow-up case with optimized queries.
    
    Returns:
        tuple: (screening_case, enrollment_case, followup_case or None)
    """
    screening, enrollment, _ = get_patient_case_chain(request, usubjid)
    
    try:
        followup = FU_CASE_28.objects.select_related(
            'USUBJID', 'USUBJID__USUBJID'
        ).prefetch_related(
            'rehospitalizations', 'antibiotics'
        ).get(USUBJID=enrollment)
        
        return screening, enrollment, followup
    except FU_CASE_28.DoesNotExist:
        return screening, enrollment, None


def save_followup_and_related(
    request,
    followup_form,
    rehospitalization_formset,
    antibiotic_formset,
    enrollment_case,
    is_create=False
):
    """
    Save follow-up and all related forms in transaction.
    
    Returns:
        FU_CASE_28 instance or None on error
    """
    try:
        with transaction.atomic():
            followup = followup_form.save(commit=False)
            
            if is_create:
                followup.USUBJID = enrollment_case
            
            set_audit_metadata(followup, request.user)
            followup.save()
            
            logger.info(f"{'Created' if is_create else 'Updated'} follow-up Day 28: {followup.USUBJID.USUBJID.USUBJID}")
            
            _save_formset(rehospitalization_formset, followup, request.user, 'rehospitalizations')
            _save_formset(antibiotic_formset, followup, request.user, 'antibiotics')
            
            return followup
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        messages.error(request, f'Lỗi validation: {e}')
        return None
    except Exception as e:
        logger.error(f"Error saving follow-up: {e}", exc_info=True)
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