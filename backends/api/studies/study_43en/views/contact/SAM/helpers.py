
# Site filtering utilities
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
)

# backends/studies/study_43en/views/contact/sample/helpers.py
"""
Contact Sample Collection Helper Functions

Provides:
- Query optimization helpers
- Data processing utilities
- Business logic functions
- Common operations for contact samples
"""

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError

# Import models
from backends.studies.study_43en.models.contact import (
    SCR_CONTACT,
    ENR_CONTACT,
    SAM_CONTACT,
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
        set_audit_metadata(sample, request.user)
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# QUERY OPTIMIZATION HELPERS
# ==========================================

def get_contact_enrollment_with_samples(usubjid):
    """
    Get contact enrollment with optimized queries
    
    Optimizations:
    - select_related: Reduce queries for foreign keys
    - prefetch_related: Optimize reverse relations
    - Single query for samples
    
    Args:
        usubjid: Contact ID (USUBJID)
    
    Returns:
        tuple: (screening_contact, enrollment_contact, samples_queryset)
    
    Raises:
        Http404: If screening or enrollment not found
    
    Example:
        screening, enrollment, samples = get_contact_enrollment_with_samples('SITE01-B-001')
    """
    # Get screening contact with enrollment prefetch
    screening_contact = get_object_or_404(
        SCR_CONTACT.objects.select_related('enrollment_contact'),
        USUBJID=usubjid
    )
    
    # Get enrollment contact with optimized queries
    enrollment_contact = get_object_or_404(
        ENR_CONTACT.objects.select_related('USUBJID').prefetch_related('sample_collections'),
        USUBJID=screening_contact
    )
    
    # Get samples ordered by type with related data
    samples = SAM_CONTACT.objects.filter(
        USUBJID=enrollment_contact
    ).select_related(
        'USUBJID',           # ENR_CONTACT
        'USUBJID__USUBJID'   # SCR_CONTACT
    ).order_by('SAMPLE_TYPE')
    
    logger.debug(f"Loaded contact enrollment with {samples.count()} samples for {usubjid}")
    
    return screening_contact, enrollment_contact, samples


def get_single_contact_sample(enrollment_contact, sample_type):
    """
    Get single contact sample with error handling
    
    Args:
        enrollment_contact: ENR_CONTACT instance
        sample_type: Sample type code ('1', '2', '3', '4')
    
    Returns:
        SAM_CONTACT instance or None
    
    Example:
        sample = get_single_contact_sample(enrollment, '1')
    """
    try:
        return SAM_CONTACT.objects.select_related(
            'USUBJID', 'USUBJID__USUBJID'
        ).get(
            USUBJID=enrollment_contact,
            SAMPLE_TYPE=sample_type
        )
    except SAM_CONTACT.DoesNotExist:
        return None


def check_contact_sample_exists(enrollment_contact, sample_type):
    """
    Quick check if contact sample exists (no object retrieval)
    
    Args:
        enrollment_contact: ENR_CONTACT instance
        sample_type: Sample type code
    
    Returns:
        bool: True if exists
    
    Example:
        if check_contact_sample_exists(enrollment, '1'):
            # Sample exists
    """
    return SAM_CONTACT.objects.filter(
        USUBJID=enrollment_contact,
        SAMPLE_TYPE=sample_type
    ).exists()


# ==========================================
# DATA PROCESSING HELPERS
# ==========================================

def process_boolean_fields(post_data):
    """
    Process boolean checkbox fields from POST data
    
    Django behavior:
    - Checked checkbox: sends 'on'
    - Unchecked checkbox: sends nothing
    
    This function converts to 'True'/'False' strings for form processing
    
    Args:
        post_data: Mutable POST data copy (QueryDict)
    
    Returns:
        Modified post_data with boolean fields as 'True'/'False' strings
    
    Example:
        post_data = request.POST.copy()
        post_data = process_boolean_fields(post_data)
    """
    boolean_fields = [
        # Sample types
        'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
        # Klebsiella findings
        'KLEBPNEU_1', 'KLEBPNEU_2', 'KLEBPNEU_3',
        # Other organisms
        'OTHERRES_1', 'OTHERRES_2', 'OTHERRES_3',
    ]
    
    for field_name in boolean_fields:
        # Checkbox is checked if field exists and value is 'on'
        is_checked = field_name in post_data and post_data[field_name] == 'on'
        post_data[field_name] = 'True' if is_checked else 'False'
    
    return post_data


def validate_sample_type(sample_type):
    """
    Validate sample type code
    
    Args:
        sample_type: Sample type code to validate
    
    Returns:
        bool: True if valid
    
    Valid types:
        '1': Sample 1 (At enrollment)
        '2': Sample 2 (10 ± 3 days)
        '3': Sample 3 (28 ± 3 days)
        '4': Sample 4 (90 ± 3 days)
    
    Example:
        if not validate_sample_type(sample_type):
            return error_response()
    """
    valid_types = ['1', '2', '3', '4']
    return sample_type in valid_types


# ==========================================
# BUSINESS LOGIC HELPERS (LESS STRICT)
# ==========================================

def clear_sample_data_if_not_collected(sample):
    """
    Clear all sample-related data if SAMPLE = False
    
    Business Rule:
    If no sample was collected, all collection details must be cleared
    
    NOTE: Same logic as patient but for contacts
    
    Args:
        sample: SAM_CONTACT instance
    
    Returns:
        Modified sample instance
    
    Example:
        if not sample.SAMPLE:
            sample = clear_sample_data_if_not_collected(sample)
    """
    if not sample.SAMPLE:
        logger.debug(f"Clearing contact sample data for {sample.USUBJID_id} - Type {sample.SAMPLE_TYPE}")
        
        # Clear all sample types
        sample.STOOL = False
        sample.THROATSWAB = False
        sample.RECTSWAB = False
        sample.BLOOD = False
        
        # Clear all collection dates
        sample.STOOLDATE = None
        sample.RECTSWABDATE = None
        sample.THROATSWABDATE = None
        sample.BLOODDATE = None
        
        # Set culture results to NoApply
        sample.CULTRES_1 = 'NoApply'
        sample.CULTRES_2 = 'NoApply'
        sample.CULTRES_3 = 'NoApply'
        
        # Clear all organism findings
        sample.KLEBPNEU_1 = False
        sample.KLEBPNEU_2 = False
        sample.KLEBPNEU_3 = False
        sample.OTHERRES_1 = False
        sample.OTHERRES_2 = False
        sample.OTHERRES_3 = False
        sample.OTHERRESSPECIFY_1 = ''
        sample.OTHERRESSPECIFY_2 = ''
        sample.OTHERRESSPECIFY_3 = ''
    
    return sample


def clear_dates_if_sample_not_selected(sample):
    """
    Clear collection dates for sample types that are not selected
    
    Business Rule:
    If a specific sample type was not collected, its date must be cleared
    
    Args:
        sample: SAM_CONTACT instance
    
    Returns:
        Modified sample instance
    """
    if not sample.STOOL:
        sample.STOOLDATE = None
    
    if not sample.THROATSWAB:
        sample.THROATSWABDATE = None
    
    if not sample.RECTSWAB:
        sample.RECTSWABDATE = None
    
    if not sample.BLOOD:
        sample.BLOODDATE = None
    
    return sample


def handle_sample_type_4_restrictions(sample):
    """
    Apply restrictions for Sample Type 4 (90 days after enrollment)
    
    Business Rule:
    Sample Type 4 does not collect blood samples
    
    Args:
        sample: SAM_CONTACT instance
    
    Returns:
        Modified sample instance
    """
    if sample.SAMPLE_TYPE == '4':
        logger.debug(f"Applying Type 4 restrictions for contact: removing blood collection")
        sample.BLOOD = False
        sample.BLOODDATE = None
    
    return sample


def apply_all_business_rules(sample):
    """
    Apply all business rules to contact sample instance
    
    Convenience function that applies all business logic in correct order
    
    Args:
        sample: SAM_CONTACT instance
    
    Returns:
        Modified sample instance with all business rules applied
    
    Example:
        sample = form.save(commit=False)
        sample = apply_all_business_rules(sample)
        sample.save()
    """
    sample = clear_sample_data_if_not_collected(sample)
    sample = clear_dates_if_sample_not_selected(sample)
    sample = handle_sample_type_4_restrictions(sample)
    
    return sample


# ==========================================
# TRANSACTION HELPERS
# ==========================================

def save_contact_sample_with_audit(sample, user, form=None):
    """
    Save contact sample with audit metadata in transaction
    
    Features:
    - Transaction safety
    - Audit metadata
    - Version increment
    - Business rules application
    - Error handling
    
    Args:
        sample: SAM_CONTACT instance (not yet saved)
        user: User object
        form: Optional form for additional validation
    
    Returns:
        tuple: (success: bool, sample: SAM_CONTACT or None, error: str or None)
    
    Example:
        success, sample, error = save_contact_sample_with_audit(sample, request.user)
        if success:
            messages.success(request, 'Saved successfully!')
        else:
            messages.error(request, error)
    """
    try:
        with transaction.atomic():
            # Apply business rules
            sample = apply_all_business_rules(sample)
            
            # Set audit metadata
            set_audit_metadata(sample, user)
            
            # Increment version
            if sample.pk:
                sample.version += 1
            
            # Save
            sample.save()
            
            logger.info(
                f" Saved contact sample: {sample.USUBJID_id} - Type {sample.SAMPLE_TYPE} "
                f"(Version: {sample.version})"
            )
            
            return True, sample, None
    
    except ValidationError as e:
        logger.error(f" Validation error: {e}")
        return False, None, f'Lỗi validation: {str(e)}'
    
    except Exception as e:
        logger.error(f" Error saving contact sample: {e}", exc_info=True)
        return False, None, f'Lỗi khi lưu: {str(e)}'


# ==========================================
# CONTEXT BUILDERS
# ==========================================

def build_contact_sample_context(form, sample, screening_contact, enrollment_contact, 
                                 usubjid, sample_type, is_new=False, is_readonly=False,
                                 extra_context=None):
    """
    Build standard context dictionary for contact sample templates
    
    Args:
        form: ContactSampleCollectionForm instance
        sample: SAM_CONTACT instance or None
        screening_contact: SCR_CONTACT instance
        enrollment_contact: ENR_CONTACT instance
        usubjid: Contact USUBJID
        sample_type: Sample type code
        is_new: Boolean indicating if this is create (vs update)
        is_readonly: Boolean indicating read-only mode
        extra_context: Optional dict with additional context
    
    Returns:
        dict: Complete context for template rendering
    
    Example:
        context = build_contact_sample_context(
            form=form,
            sample=sample,
            screening_contact=screening,
            enrollment_contact=enrollment,
            usubjid=usubjid,
            sample_type='1',
            is_new=False
        )
    """
    from datetime import date
    
    # Base context
    context = {
        'form': form,
        'sample': sample,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'sample_type_display': dict(SAM_CONTACT.SampleTypeChoices.choices).get(
            sample_type, f"Sample {sample_type}"
        ),
        'is_new': is_new,
        'is_readonly': is_readonly,
        'is_view_only': is_readonly,
        'today': date.today(),
        'selected_site_id': screening_contact.SITEID,
    }
    
    # Add version if updating existing sample
    if sample and sample.pk:
        context['current_version'] = sample.version
    
    # Merge extra context if provided
    if extra_context:
        context.update(extra_context)
    
    return context


def get_sample_type_display(sample_type):
    """
    Get human-readable display name for sample type
    
    Args:
        sample_type: Sample type code ('1', '2', '3', '4')
    
    Returns:
        str: Display name
    
    Example:
        display = get_sample_type_display('1')  # "Sample 1 (At enrollment)"
    """
    return dict(SAM_CONTACT.SampleTypeChoices.choices).get(
        sample_type, 
        f"Sample {sample_type}"
    )


# ==========================================
# READONLY FIELD LISTS
# ==========================================

def get_readonly_fields_for_change_detection():
    """
    Get list of fields that should be excluded from change detection
    
    Returns:
        list: Field names to exclude from change detection
    """
    return [
        'USUBJID',                      # Foreign key - set at creation
        'SAMPLE_TYPE',                  # Set at creation, never changes
        'SAMPLE_STATUS',                # Auto-calculated by model
        'version',                      # Audit field
        'last_modified_at',             # Audit field
        'last_modified_by_id',          # Audit field
        'last_modified_by_username',    # Audit field
    ]


# ==========================================
# LOGGING HELPERS
# ==========================================

def log_form_errors(form, form_name="Form"):
    """
    Log form validation errors in readable format
    
    Args:
        form: Django form with errors
        form_name: Name for logging (default: "Form")
    
    Example:
        if not form.is_valid():
            log_form_errors(form, "ContactSampleCollectionForm")
    """
    if form.errors:
        logger.warning(f" {form_name} validation errors:")
        for field, errors in form.errors.items():
            for error in errors:
                logger.warning(f"  - {field}: {error}")
