# backends/api/studies/study_44en/views/household/case_helpers.py
"""
Household Case Helper Functions - FIXED

Shared utilities for household case CRUD views.
Following Django development rules: Backend-first approach.

FIXED: Removed deleted_objects (custom formset handles deletion internally)
SIMPLIFIED: Removed unnecessary logic
"""

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib import messages

from backends.studies.study_44en.models.household import HH_CASE, HH_Member
from backends.audit_logs.models import AuditLog, AuditLogDetail

logger = logging.getLogger(__name__)


# ==========================================
# AUDIT METADATA (TODO: Move to centralized helpers)
# ==========================================

def set_audit_metadata(instance, user):
    """
    Set audit fields on instance
    
    📝 TODO: Move to backends/audit_log/utils/view_helpers.py
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
    
    📝 TODO: Move to backends/audit_log/utils/view_helpers.py
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
    
    📝 TODO: Move to backends/audit_log/utils/view_helpers.py
    """
    for form in formset.forms:
        make_form_readonly(form)


# ==========================================
# DATA RETRIEVAL
# ==========================================

def get_household_with_related(request, hhid):
    """
    Get household with members
    
    Returns:
        tuple: (household, members)
        
    Note:
        - Returns household with all related members
        - Optimized with order_by
    """
    logger.info(f"📥 Fetching household {hhid} with members...")
    
    # Get household (with 404 if not found)
    household = get_object_or_404(HH_CASE, HHID=hhid)
    logger.info(f"   Found household: {household.HHID}")
    
    # Get all members
    members = HH_Member.objects.filter(HHID=household).order_by('MEMBER_NUM')
    
    logger.info(f"   Found {members.count()} members")
    
    return household, members


# ==========================================
# TRANSACTION HANDLER - SIMPLIFIED
# ==========================================

def save_household_and_related(request, household_form, member_formset, is_create=False, change_reasons=None, all_changes=None):
    """
    Save household and members in transaction
    
    SIMPLIFIED: Custom formset already handles deletion internally
    
    Args:
        request: HttpRequest
        household_form: HH_CASEForm instance
        member_formset: HH_MemberFormSet instance (custom with save() method)
        is_create: bool - True if creating new household
        change_reasons: dict - Mapping of field_name -> reason (for audit log)
        all_changes: list - List of change dicts with field, old_value, new_value
    
    Returns:
        HH_CASE instance or None on error
    """
    logger.info("="*80)
    logger.info(f"💾 SAVING HOUSEHOLD (is_create={is_create})")
    logger.info("="*80)
    
    try:
        with transaction.atomic(using='db_study_44en'):
            # ===================================
            # 1. SAVE MAIN HOUSEHOLD FORM
            # ===================================
            logger.info("📝 Step 1: Saving household form...")
            
            household = household_form.save(commit=False)
            
            set_audit_metadata(household, request.user)
            
            if is_create and hasattr(household, 'version'):
                household.version = 0
            
            household.save()
            
            logger.info(f"   Saved household: {household.HHID}")
            
            # ===================================
            # 2. SAVE MEMBER FORMSET
            # ===================================
            logger.info("📝 Step 2: Saving members...")
            
            # FIX: Custom formset.save() already handles:
            # - Filtering empty forms
            # - Deleting marked forms
            # - Setting audit metadata (if needed)
            # - Saving valid forms
            
            # Just call save() - formset handles everything
            saved_members = member_formset.save(commit=False)
            
            # Set HHID and audit metadata for each saved member
            for member in saved_members:
                member.HHID = household
                set_audit_metadata(member, request.user)
                member.save()
                logger.info(f"      Saved member: {member.MEMBER_NUM}")
            
            logger.info(f"   Saved {len(saved_members)} members")
            
            # ===================================
            # 3. SAVE AUDIT LOG (if reasons provided)
            # ===================================
            if change_reasons and all_changes:
                logger.info("📝 Step 3: Saving audit log...")
                
                # Combine all reasons into one string for main audit log
                combined_reason = "; ".join([
                    f"{field}: {reason}" 
                    for field, reason in change_reasons.items()
                ])
                
                # Create main audit log entry
                audit_log = AuditLog(
                    user_id=request.user.id,
                    username=request.user.username,
                    action='UPDATE',
                    model_name='HH_CASE',
                    patient_id=str(household.HHID),
                    SITEID=getattr(household, 'SITEID', None),
                    reason=combined_reason,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    session_id=request.session.session_key,
                )
                
                # Store temp data for checksum calculation
                old_data = {change['field']: change['old_value'] for change in all_changes}
                new_data = {change['field']: change['new_value'] for change in all_changes}
                
                audit_log._temp_checksum_data = {
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'action': 'UPDATE',
                    'model_name': 'HH_CASE',
                    'patient_id': str(household.HHID),
                    'old_data': old_data,
                    'new_data': new_data,
                    'reason': combined_reason,
                }
                
                audit_log.save()
                logger.info(f"      Created main audit log entry #{audit_log.id}")
                
                # Create detail entries for each field change
                for change in all_changes:
                    field_name = change['field']
                    reason = change_reasons.get(field_name, 'No reason provided')
                    
                    detail = AuditLogDetail(
                        audit_log=audit_log,
                        field_name=field_name,
                        old_value=str(change.get('old_value', '')),
                        new_value=str(change.get('new_value', '')),
                        reason=reason,
                    )
                    detail.save()
                    logger.info(f"      Saved detail for {field_name}")
                
                logger.info(f"   Saved audit log with {len(all_changes)} detail entries")
            
            logger.info("="*80)
            logger.info(f"SAVE COMPLETE - Household {household.HHID}")
            logger.info("="*80)
            
            return household
            
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ SAVE FAILED: {e}")
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
        logger.warning(f"❌ {form_name} errors: {form.errors}")
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

def check_household_exists(hhid):
    """
    Check if household exists
    
    Returns:
        bool: True if exists, False otherwise
    """
    return HH_CASE.objects.filter(HHID=hhid).exists()


def get_household_summary(household):
    """
    Get summary statistics for household
    
    Returns:
        dict: Summary data
    """
    members = HH_Member.objects.filter(HHID=household)
    
    # Calculate age for members with birth year
    current_year = 2025  # or use date.today().year
    adults = 0
    children = 0
    
    for member in members:
        if member.BIRTH_YEAR:
            age = current_year - member.BIRTH_YEAR
            if age >= 18:
                adults += 1
            else:
                children += 1
    
    return {
        'total_members': members.count(),
        'adults': adults,
        'children': children,
        'has_respondent': household.RESPONDENT_MEMBER_NUM is not None,
    }