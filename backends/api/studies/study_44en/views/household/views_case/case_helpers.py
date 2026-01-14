# backends/api/studies/study_44en/views/household/case_helpers.py

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib import messages

from backends.studies.study_44en.models.household import HH_CASE, HH_Member
from backends.studies.study_44en.models.per_data import HH_PERSONAL_DATA
from backends.studies.study_44en.models import AuditLog, AuditLogDetail

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields on instance"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


def make_form_readonly(form):
    """Make all form fields readonly"""
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({'readonly': True, 'disabled': True})


def make_formset_readonly(formset):
    """Make all formset fields readonly"""
    for form in formset.forms:
        make_form_readonly(form)


def get_household_with_related(request, hhid):
    """Get household with members"""
    logger.info(f"📥 Fetching household {hhid} with members...")
    
    household = get_object_or_404(HH_CASE, HHID=hhid)
    members = HH_Member.objects.filter(HHID=household).order_by('MEMBER_NUM')
    
    logger.info(f"   Found household: {household.HHID}, {members.count()} members")
    
    return household, members


def save_household_and_related(request, household_form, personal_data_form, member_formset, 
                                is_create=False, change_reasons=None, all_changes=None):
    """
    Save household, personal data, and members in transaction
    
    Args:
        request: HttpRequest
        household_form: HH_CASEForm instance
        personal_data_form: HH_PersonalDataForm instance (NEW)
        member_formset: HH_MemberFormSet instance
        is_create: bool
        change_reasons: dict
        all_changes: list
    
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
            logger.info(" Step 1: Saving household form...")
            
            household = household_form.save(commit=False)
            set_audit_metadata(household, request.user)
            
            if is_create and hasattr(household, 'version'):
                household.version = 0
            
            household.save()
            logger.info(f"   Saved household: {household.HHID}")
            
            # ===================================
            # 2. SAVE PERSONAL DATA (ADDRESS)
            # ===================================
            logger.info(" Step 2: Saving personal data (address)...")
            
            personal_data = personal_data_form.save(commit=False)
            personal_data.HHID = household
            set_audit_metadata(personal_data, request.user)
            
            # Set default city if empty
            if not personal_data.CITY:
                personal_data.CITY = 'Ho Chi Minh City'
            
            personal_data.save()
            logger.info(f"   Saved personal data: STREET={personal_data.STREET}, WARD={personal_data.WARD}")
            
            # ===================================
            # 3. SAVE MEMBER FORMSET
            # ===================================
            logger.info(" Step 3: Saving members...")
            
            saved_members = member_formset.save(commit=False)
            
            for member in saved_members:
                member.HHID = household
                set_audit_metadata(member, request.user)
                member.save()
                logger.info(f"      Saved member: {member.MEMBER_NUM}")
            
            logger.info(f"   Saved {len(saved_members)} members")
            
            # ===================================
            # 4. SAVE AUDIT LOG (if reasons provided)
            # ===================================
            if change_reasons and all_changes:
                logger.info(" Step 4: Saving audit log...")
                
                combined_reason = "; ".join([
                    f"{field}: {reason}" 
                    for field, reason in change_reasons.items()
                ])
                
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
                
                logger.info(f"   Saved audit log with {len(all_changes)} detail entries")
            
            logger.info(f"SAVE COMPLETE - Household {household.HHID}")
            
            return household
            
    except Exception as e:
        logger.error(f"❌ SAVE FAILED: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu: {str(e)}')
        return None


def log_form_errors(form, form_name):
    """Log form validation errors"""
    if form.errors:
        logger.warning(f"❌ {form_name} errors: {form.errors}")
        return True
    return False


def log_all_form_errors(forms_dict):
    """Log all form validation errors"""
    forms_with_errors = []
    for name, form in forms_dict.items():
        if log_form_errors(form, name):
            forms_with_errors.append(name)
    return forms_with_errors


def check_household_exists(hhid):
    """Check if household exists"""
    return HH_CASE.objects.filter(HHID=hhid).exists()


def get_household_summary(household):
    """Get summary statistics for household"""
    members = HH_Member.objects.filter(HHID=household)
    
    current_year = 2025
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
