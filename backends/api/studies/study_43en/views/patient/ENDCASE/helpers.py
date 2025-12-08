
# Site filtering utilities
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
)

# backends/studies/study_43en/views/patient/endcase/helpers.py
"""
End Case CRF Helper Functions

Provides:
- Query optimization helpers
- Form utilities
- Audit helpers
- Context builders
"""

import logging
from django.shortcuts import get_object_or_404

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
    EndCaseCRF,
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
        set_audit_metadata(endcase, request.user)
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# QUERY OPTIMIZATION HELPERS
# ==========================================

def get_endcase_with_related(request, usubjid):
    """
    Get end case with optimized queries
    
    Optimizations:
    - select_related: Reduce queries for foreign keys
    - Single query structure
    
    Args:
        usubjid: Patient ID (USUBJID)
    
    Returns:
        tuple: (screening_case, enrollment_case, endcase or None)
    
    Raises:
        Http404: If screening or enrollment not found
    
    Example:
        screening, enrollment, endcase = get_endcase_with_related('SITE01-A-001')
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
    
    # Get end case if exists
    try:
        endcase = EndCaseCRF.objects.select_related(
            'USUBJID',           # ENR_CASE
            'USUBJID__USUBJID'   # SCR_CASE
        ).get(USUBJID=enrollment_case)
        
        logger.debug(f"Loaded end case for {usubjid}")
        return screening_case, enrollment_case, endcase
    
    except EndCaseCRF.DoesNotExist:
        return screening_case, enrollment_case, None


# ==========================================
# FORM UTILITIES
# ==========================================

def make_form_readonly(form):
    """
    Make all form fields readonly
    
    Args:
        form: Django form
    
    Example:
        form = EndCaseCRFForm(instance=endcase)
        make_form_readonly(form)
    """
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': True,
            'disabled': True
        })


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
        if log_form_errors(form, "EndCaseCRFForm"):
            messages.error(request, 'Vui lòng kiểm tra lại form')
    """
    if form.errors:
        logger.warning(f" {form_name} validation errors:")
        for field, errors in form.errors.items():
            for error in errors:
                logger.warning(f"  - {field}: {error}")
        return True
    return False


# ==========================================
# CONTEXT BUILDERS
# ==========================================

def build_endcase_context(
    form,
    endcase,
    screening_case,
    enrollment_case,
    is_create,
    is_readonly,
    extra_context=None
):
    """
    Build standard context dictionary for end case templates
    
    Args:
        form: EndCaseCRFForm instance
        endcase: EndCaseCRF instance or None
        screening_case: SCR_CASE instance
        enrollment_case: ENR_CASE instance
        is_create: Boolean indicating if this is create (vs update)
        is_readonly: Boolean indicating read-only mode
        extra_context: Optional dict with additional context
    
    Returns:
        dict: Complete context for template rendering
    
    Example:
        context = build_endcase_context(
            form=form,
            endcase=endcase,
            screening_case=screening,
            enrollment_case=enrollment,
            is_create=False,
            is_readonly=False
        )
    """
    from datetime import date
    
    # Base context
    context = {
        'form': form,
        'endcase': endcase,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'is_create': is_create,
        'is_readonly': is_readonly,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    # Add version if updating existing end case
    if endcase and endcase.pk:
        context['current_version'] = endcase.version
    
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
    - Auto-calculated (STUDYCOMPLETED)
    - Audit fields (version, timestamps, user IDs)
    
    Returns:
        list: Field names to exclude
    
    Example:
        READONLY_FIELDS = get_readonly_fields_for_change_detection()
        old_data = {k: v for k, v in old_data.items() if k not in READONLY_FIELDS}
    """
    return [
        'USUBJID',                      # Foreign key
        'STUDYCOMPLETED',               # Auto-calculated by model
        'version',                      # Audit field
        'last_modified_at',             # Audit field
        'last_modified_by_id',          # Audit field
        'last_modified_by_username',    # Audit field
    ]


# ==========================================
# BUSINESS LOGIC HELPERS
# ==========================================

def validate_visit_sequence(endcase):
    """
    Validate visit completion sequence
    
    Business Rule:
    Cannot complete later visits without completing earlier ones
    
    Args:
        endcase: EndCaseCRF instance
    
    Returns:
        list: List of validation errors (empty if valid)
    
    Example:
        errors = validate_visit_sequence(endcase)
        if errors:
            for error in errors:
                messages.warning(request, error)
    """
    errors = []
    
    # V4 requires V3
    if endcase.V4COMPLETED and not endcase.V3COMPLETED:
        errors.append('Không thể hoàn thành V4 khi chưa hoàn thành V3')
    
    # V3 requires V2
    if endcase.V3COMPLETED and not endcase.V2COMPLETED:
        errors.append('Không thể hoàn thành V3 khi chưa hoàn thành V2')
    
    # V2 requires V1
    if endcase.V2COMPLETED and not endcase.VICOMPLETED:
        errors.append('Không thể hoàn thành V2 khi chưa hoàn thành V1')
    
    return errors


def get_completion_status_summary(endcase):
    """
    Get comprehensive completion status summary
    
    Args:
        endcase: EndCaseCRF instance
    
    Returns:
        dict: Detailed completion information
    
    Example:
        summary = get_completion_status_summary(endcase)
        context['completion_summary'] = summary
    """
    if not endcase:
        return None
    
    return {
        # Visit completion
        'total_visits': endcase.total_visits_completed,
        'completion_rate': f"{endcase.completion_rate:.0f}%",
        'all_completed': endcase.all_visits_completed,
        'visits': {
            'V1': endcase.VICOMPLETED,
            'V2': endcase.V2COMPLETED,
            'V3': endcase.V3COMPLETED,
            'V4': endcase.V4COMPLETED,
        },
        
        # Study status
        'study_completed': endcase.STUDYCOMPLETED,
        'has_early_termination': endcase.has_early_termination,
        'termination_reason': endcase.termination_reason,
        
        # Duration
        'study_duration_days': endcase.study_duration_days,
        
        # Flags
        'is_withdrawn': endcase.is_withdrawn,
        'is_incomplete': endcase.is_incomplete,
        'is_lost_to_followup': endcase.is_lost_to_followup,
        
        # Incomplete reasons
        'incomplete_reasons': endcase.incomplete_reason_list if endcase.is_incomplete else [],
    }


def check_can_complete_study(endcase):
    """
    Check if study can be marked as completed
    
    Args:
        endcase: EndCaseCRF instance
    
    Returns:
        tuple: (can_complete: bool, reasons: list)
    
    Example:
        can_complete, reasons = check_can_complete_study(endcase)
        if not can_complete:
            messages.warning(request, 'Không thể hoàn thành: ' + ', '.join(reasons))
    """
    reasons = []
    
    # Check all visits completed
    if not endcase.all_visits_completed:
        reasons.append('Chưa hoàn thành đủ 4 visits')
    
    # Check no early termination
    if endcase.has_early_termination:
        reasons.append(f'Có kết thúc sớm: {endcase.termination_reason}')
    
    # Check end date provided
    if not endcase.ENDDATE:
        reasons.append('Chưa có ngày kết thúc')
    
    can_complete = len(reasons) == 0
    
    return can_complete, reasons


# ==========================================
# STATISTICS HELPERS
# ==========================================

def get_site_completion_stats(site_id=None):
    """
    Get completion statistics for a site
    
    Args:
        site_id: Site ID to filter (None for all sites)
    
    Returns:
        dict: Completion statistics
    
    Example:
        stats = get_site_completion_stats('003')
        context['site_stats'] = stats
    """
    qs = EndCaseCRF.objects.all()
    
    if site_id:
        qs = qs.filter(USUBJID__USUBJID__SITEID=site_id)
    
    total = qs.count()
    
    if total == 0:
        return None
    
    stats = {
        'total': total,
        'completed': qs.filter(STUDYCOMPLETED=True).count(),
        'withdrawn': qs.exclude(
            WITHDRAWREASON='na'
        ).count(),
        'incomplete': qs.filter(INCOMPLETE='yes').count(),
        'lost_to_followup': qs.filter(LOSTTOFOLLOWUP='yes').count(),
    }
    
    # Calculate percentages
    stats['completion_rate'] = (stats['completed'] / total) * 100
    stats['withdrawal_rate'] = (stats['withdrawn'] / total) * 100
    stats['ltfu_rate'] = (stats['lost_to_followup'] / total) * 100
    
    return stats