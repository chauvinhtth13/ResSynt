# backends/api/studies/study_44en/views/individual/individual_helpers.py
"""
Individual Helper Functions - Following Household Pattern

Shared utilities for individual CRUD views with audit support.
"""

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib import messages

from backends.studies.study_44en.models.individual import Individual
from backends.studies.study_44en.models import AuditLog, AuditLogDetail

logger = logging.getLogger(__name__)


# ==========================================
# AUDIT METADATA
# ==========================================

def set_audit_metadata(instance, user):
    """
    Set audit fields on instance
    """
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# READ-ONLY HELPERS
# ==========================================

def make_form_readonly(form):
    """
    Make all form fields readonly
    """
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({
            'readonly': True,
            'disabled': True
        })


# ==========================================
# DATA RETRIEVAL
# ==========================================

def get_individual_with_related(request, subjectid):
    """
    Get individual with related data
    
    Returns:
        Individual instance
    """
    logger.info(f"📥 Fetching individual {subjectid}...")
    
    # Get individual (with 404 if not found)
    individual = get_object_or_404(Individual, SUBJECTID=subjectid)
    logger.info(f"   Found individual: {individual.SUBJECTID}")
    
    return individual


# ==========================================
# TRANSACTION HANDLER
# ==========================================

def save_individual(request, individual_form, is_create=False, change_reasons=None, all_changes=None):
    """
    Save individual in transaction with optional audit
    
    Args:
        request: HttpRequest
        individual_form: IndividualForm instance
        is_create: bool - True if creating new individual
        change_reasons: dict - Mapping of field_name -> reason (for audit log)
        all_changes: list - List of change dicts with field, old_value, new_value
    
    Returns:
        Individual instance or None on error
    """
    logger.info("="*80)
    logger.info(f"💾 SAVING INDIVIDUAL (is_create={is_create})")
    logger.info("="*80)
    
    try:
        with transaction.atomic(using='db_study_44en'):
            # ===================================
            # 1. SAVE INDIVIDUAL FORM
            # ===================================
            logger.info("📝 Step 1: Saving individual form...")
            
            individual = individual_form.save(commit=False)
            
            set_audit_metadata(individual, request.user)
            
            if is_create and hasattr(individual, 'version'):
                individual.version = 0
            
            individual.save()
            
            subjectid = individual.MEMBERID.MEMBERID if individual.MEMBERID else individual.SUBJECTID
            logger.info(f"   Saved individual: {subjectid}")
            
            # ===================================
            # 2. SAVE AUDIT LOG (if reasons provided)
            # ===================================
            if change_reasons and all_changes:
                logger.info("📋 Step 2: Saving audit log...")
                
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
                    model_name='Individual',
                    patient_id=str(subjectid),
                    SITEID=getattr(individual, 'SITEID', None),
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
                    'model_name': 'Individual',
                    'patient_id': str(subjectid),
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
            logger.info(f"SAVE COMPLETE - Individual {subjectid}")
            logger.info("="*80)
            
            return individual
            
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


# ==========================================
# BUSINESS LOGIC HELPERS
# ==========================================

def check_individual_exists(subjectid):
    """
    Check if individual exists
    
    Returns:
        bool: True if exists, False otherwise
    """
    return Individual.objects.filter(SUBJECTID=subjectid).exists()


def get_individual_summary(individual):
    """
    Get summary statistics for individual
    
    Returns:
        dict: Summary data
    """
    # Get related counts
    exposure_count = 1 if hasattr(individual, 'exposure') and individual.exposure else 0
    followup_count = individual.follow_ups.count() if hasattr(individual, 'follow_ups') else 0
    sample_count = individual.samples.count() if hasattr(individual, 'samples') else 0
    
    return {
        'exposure_count': exposure_count,
        'followup_count': followup_count,
        'sample_count': sample_count,
    }
