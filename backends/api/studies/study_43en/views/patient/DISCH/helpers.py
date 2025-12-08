
# Site filtering utilities
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
)

# backends/studies/study_43en/views/patient/discharge/helpers.py
"""
Discharge Helper Functions

Provides:
- Query optimization helpers
- Transaction handlers
- Form utilities
- Audit helpers
- Context builders
"""

import logging
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
    DISCH_CASE,
    DischargeICD,
)

logger = logging.getLogger(__name__)


# ==========================================
# AUDIT HELPERS
# ==========================================

def set_audit_metadata(instance, user):
    """
    Set audit fields on instance
    
    Args:
        instance: Model instance with audit fields
        user: User object
    
    Usage:
        set_audit_metadata(discharge, request.user)
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# QUERY OPTIMIZATION HELPERS
# ==========================================

def get_discharge_with_related(request, usubjid):
    """
    Get discharge case with optimized queries
    
    Optimizations:
    - select_related: Reduce queries for foreign keys
    - prefetch_related: Optimize reverse relations
    
    Args:
        usubjid: Patient ID (USUBJID)
    
    Returns:
        tuple: (screening_case, enrollment_case, discharge_case or None)
    
    Raises:
        Http404: If screening or enrollment not found
    
    Example:
        screening, enrollment, discharge = get_discharge_with_related('SITE01-A-001')
    """
    # Get site filtering parameters
    site_filter, filter_type = get_site_filter_params(request)

    # Get screening case
    #  Get with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE,
        site_filter,
        filter_type,
        USUBJID=usubjid
    )
    
    # Get enrollment case
    enrollment_case = get_object_or_404(
        ENR_CASE.objects.select_related('USUBJID'),
        USUBJID=screening_case
    )
    
    # Get discharge case if exists
    try:
        discharge_case = DISCH_CASE.objects.select_related(
            'USUBJID',           # ENR_CASE
            'USUBJID__USUBJID'   # SCR_CASE
        ).prefetch_related(
            'icd_codes'          # DischargeICD
        ).get(USUBJID=enrollment_case)
        
        logger.debug(f"Loaded discharge with {discharge_case.icd_code_count} ICD codes")
        return screening_case, enrollment_case, discharge_case
    
    except DISCH_CASE.DoesNotExist:
        return screening_case, enrollment_case, None


# ==========================================
# TRANSACTION HANDLER
# ==========================================

def save_discharge_and_related(
    request,
    discharge_form,
    icd_formset,
    enrollment_case,
    is_create=False
):
    """
    Save discharge and ICD codes in transaction
    
    Features:
    - Transaction safety
    - Audit metadata
    - Version increment
    - Error handling
    
    Args:
        request: HttpRequest
        discharge_form: DischargeCaseForm
        icd_formset: DischargeICDFormSet
        enrollment_case: ENR_CASE instance
        is_create: bool - True if creating new discharge
    
    Returns:
        DISCH_CASE instance or None on error
    
    Example:
        discharge = save_discharge_and_related(
            request=request,
            discharge_form=form,
            icd_formset=formset,
            enrollment_case=enrollment,
            is_create=True
        )
    """
    try:
        with transaction.atomic():
            # 1. Save discharge case (main)
            discharge = discharge_form.save(commit=False)
            
            if is_create:
                discharge.USUBJID = enrollment_case
            
            # Set audit metadata
            set_audit_metadata(discharge, request.user)
            
            # Save
            discharge.save()
            
            logger.info(
                f"{'Created' if is_create else 'Updated'} discharge: "
                f"{discharge.USUBJID.USUBJID.USUBJID}"
            )
            
            # 2. Save ICD codes
            _save_icd_formset(icd_formset, discharge, request.user)
            
            return discharge
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        messages.error(request, f'Lỗi validation: {e}')
        return None
    
    except Exception as e:
        logger.error(f"Error saving discharge: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu thông tin ra viện: {str(e)}')
        return None


def _save_icd_formset(formset, discharge_case, user):
    """
    Helper to save ICD formset
    
    Args:
        formset: DischargeICDFormSet
        discharge_case: DISCH_CASE instance
        user: User object
    """
    # Get instances to save (excluding deleted)
    instances = formset.save(commit=False)
    
    # Save each ICD code
    for instance in instances:
        instance.USUBJID = discharge_case
        set_audit_metadata(instance, user)
        instance.save()
    
    # Handle deletions
    for obj in formset.deleted_objects:
        logger.info(f"Deleting ICD code: {obj.ICDCODE}")
        obj.delete()
    
    # Save m2m relationships (if any)
    formset.save_m2m()
    
    logger.info(f"Saved {len(instances)} ICD codes, deleted {len(formset.deleted_objects)}")


# ==========================================
# FORM UTILITIES
# ==========================================

def make_form_readonly(form):
    """
    Make all form fields readonly
    
    Args:
        form: Django form
    
    Example:
        form = DischargeCaseForm(instance=discharge)
        make_form_readonly(form)
    """
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': True,
            'disabled': True
        })


def make_formset_readonly(formset):
    """
    Make all formset fields readonly
    
    Args:
        formset: Django formset
    
    Example:
        formset = DischargeICDFormSet(instance=discharge)
        make_formset_readonly(formset)
    """
    for form in formset.forms:
        make_form_readonly(form)


# ==========================================
# VALIDATION HELPERS
# ==========================================

def log_form_errors(form, form_name="Form"):
    """
    Log form validation errors
    
    Args:
        form: Django form with errors
        form_name: Name for logging
    
    Returns:
        bool: True if form has errors
    
    Example:
        if log_form_errors(form, "DischargeCaseForm"):
            messages.error(request, 'Vui lòng kiểm tra lại form')
    """
    if form.errors:
        logger.warning(f" {form_name} validation errors:")
        for field, errors in form.errors.items():
            for error in errors:
                logger.warning(f"  - {field}: {error}")
        return True
    return False


def log_all_form_errors(forms_dict):
    """
    Log all form validation errors
    
    Args:
        forms_dict: Dict of {form_name: form_instance}
    
    Returns:
        list: Names of forms with errors
    
    Example:
        forms_with_errors = log_all_form_errors({
            'Discharge Form': discharge_form,
            'ICD Codes': icd_formset,
        })
    """
    forms_with_errors = []
    
    for name, form in forms_dict.items():
        if log_form_errors(form, name):
            forms_with_errors.append(name)
    
    return forms_with_errors


def collect_validation_errors(discharge_form, icd_formset):
    """
    Collect all validation errors for modal display
    
    Args:
        discharge_form: DischargeCaseForm
        icd_formset: DischargeICDFormSet
    
    Returns:
        list: List of error dicts with 'field' and 'message'
    
    Example:
        validation_errors = collect_validation_errors(form, formset)
        context['validation_errors'] = validation_errors
        context['show_validation_modal'] = True
    """
    validation_errors = []
    
    # Main form errors
    for field_name, errors in discharge_form.errors.items():
        field_label = discharge_form.fields.get(field_name).label if field_name in discharge_form.fields else field_name
        for error in errors:
            validation_errors.append({
                'field': field_label or field_name,
                'message': str(error)
            })
    
    # Main form non-field errors
    for error in discharge_form.non_field_errors():
        validation_errors.append({
            'field': 'Form chính',
            'message': str(error)
        })
    
    # ICD formset errors
    for i, form in enumerate(icd_formset.forms):
        if form.errors:
            for field_name, errors in form.errors.items():
                if field_name == '__all__':
                    field_label = f"ICD Code #{i+1}"
                else:
                    field_label = f"ICD Code #{i+1} - {form.fields.get(field_name).label if field_name in form.fields else field_name}"
                for error in errors:
                    validation_errors.append({
                        'field': field_label,
                        'message': str(error)
                    })
    
    # ICD formset non-form errors
    for error in icd_formset.non_form_errors():
        validation_errors.append({
            'field': 'ICD Codes (Formset)',
            'message': str(error)
        })
    
    return validation_errors


# ==========================================
# CONTEXT BUILDERS
# ==========================================

def build_discharge_context(
    discharge_form,
    icd_formset,
    screening_case,
    enrollment_case,
    discharge_case,
    is_create,
    is_readonly,
    extra_context=None
):
    """
    Build standard context dictionary for discharge templates
    
    Args:
        discharge_form: DischargeCaseForm instance
        icd_formset: DischargeICDFormSet instance
        screening_case: SCR_CASE instance
        enrollment_case: ENR_CASE instance
        discharge_case: DISCH_CASE instance or None
        is_create: Boolean indicating if this is create (vs update)
        is_readonly: Boolean indicating read-only mode
        extra_context: Optional dict with additional context
    
    Returns:
        dict: Complete context for template rendering
    
    Example:
        context = build_discharge_context(
            discharge_form=form,
            icd_formset=formset,
            screening_case=screening,
            enrollment_case=enrollment,
            discharge_case=discharge,
            is_create=False,
            is_readonly=False
        )
    """
    from datetime import date
    
    # Base context
    context = {
        'discharge_form': discharge_form,
        'icd_formset': icd_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'discharge_case': discharge_case,
        'is_create': is_create,
        'is_readonly': is_readonly,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    # Add version if updating existing discharge
    if discharge_case and discharge_case.pk:
        context['current_version'] = discharge_case.version
    
    # Merge extra context if provided
    if extra_context:
        context.update(extra_context)
    
    return context


# ==========================================
# CHANGE DETECTION HELPERS
# ==========================================

def get_readonly_fields_for_change_detection():
    """
    Get list of fields excluded from change detection
    
    These fields are:
    - Foreign keys (USUBJID)
    - Auto-populated (EVENT, STUDYID, SITEID, SUBJID, INITIAL)
    - Audit fields (version, timestamps, user IDs)
    
    Returns:
        list: Field names to exclude
    
    Example:
        READONLY_FIELDS = get_readonly_fields_for_change_detection()
        old_data = {k: v for k, v in old_data.items() if k not in READONLY_FIELDS}
    """
    return [
        'USUBJID',                      # Foreign key
        'EVENT',                        # Auto-populated
        'STUDYID',                      # Auto-populated
        'SITEID',                       # Auto-populated
        'SUBJID',                       # Auto-populated
        'INITIAL',                      # Auto-populated
        'version',                      # Audit field
        'last_modified_at',             # Audit field
        'last_modified_by_id',          # Audit field
        'last_modified_by_username',    # Audit field
    ]


def collect_change_reasons(request, field_changes, min_length=3):
    """
    Collect change reasons from POST data
    
    Args:
        request: HttpRequest
        field_changes: List of change dicts from ChangeDetector
        min_length: Minimum length for reason (default: 3)
    
    Returns:
        tuple: (reasons_data: dict, missing_reasons: list)
    
    Example:
        reasons_data, missing = collect_change_reasons(request, changes)
        if missing:
            # Show reason form modal
    """
    reasons_data = {}
    
    for change in field_changes:
        field_name = change['field']
        reason_key = f'reason_{field_name}'
        reason = request.POST.get(reason_key, '').strip()
        
        # Validate reason (minimum length)
        if reason and len(reason) >= min_length:
            reasons_data[field_name] = reason
    
    # Find missing reasons
    required_fields = [c['field'] for c in field_changes]
    missing_reasons = [f for f in required_fields if f not in reasons_data]
    
    logger.debug(f"Collected {len(reasons_data)}/{len(required_fields)} reasons")
    
    return reasons_data, missing_reasons


def build_combined_reason(field_changes, reasons_data):
    """
    Build combined reason string for audit log
    
    Args:
        field_changes: List of change dicts
        reasons_data: Dict of field_name -> reason
    
    Returns:
        str: Combined reason string
    
    Example:
        combined = build_combined_reason(changes, reasons)
        # "DISCHSTATUS: Status updated; DEATHCAUSE: Additional info"
    """
    return "\n".join([
        f"{change['field']}: {reasons_data.get(change['field'], 'N/A')}"
        for change in field_changes
    ])