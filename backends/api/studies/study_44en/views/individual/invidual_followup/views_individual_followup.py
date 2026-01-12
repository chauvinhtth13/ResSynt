# backends/api/studies/study_44en/views/individual/views_individual_followup.py

"""
Individual Follow-up Views for Study 44EN
Handles follow-up visits with symptoms and hospitalization data

REFACTORED: Full Audit Log Support (following exposure pattern)
- Manual change detection for flat fields
- Reason modal workflow
- Audit log creation via decorator
"""

import logging
from datetime import date, datetime
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.individual import Individual, Individual_FollowUp
from backends.studies.study_44en.forms.individual import Individual_FollowUpForm
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals

# Import audit utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.validator import ReasonValidator

# Import followup helpers with change detection
from .helpers_followup import (
    set_audit_metadata,
    make_form_readonly,
    save_symptoms,
    save_followup_hospitalizations,
    save_followup_medications,
    load_symptoms,
    load_followup_hospitalizations,
    load_followup_medications,
    # NEW: Change detection for audit log
    detect_followup_form_field_changes,
    detect_followup_flat_field_changes,
)

from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    require_crf_delete,
)


logger = logging.getLogger(__name__)


def parse_date_string(date_str):
    """
    Parse date string from dd/mm/yyyy or yyyy-mm-dd format to date object.
    Returns None if parsing fails or input is empty.
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Try dd/mm/yyyy format first (datepicker format)
    for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


# ==========================================
# LIST VIEW
# ==========================================

@login_required
def individual_followup_list(request, subjectid):
    """
    List all follow-ups for an individual with fixed 3 visit times
    """
    logger.info("=" * 80)
    logger.info("=== 📋 INDIVIDUAL FOLLOW-UP LIST ===")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get all follow-ups
    followups = Individual_FollowUp.objects.filter(
        MEMBERID=individual
    )
    
    # Create dictionary: visit_time → followup object
    followups_by_time = {}
    for followup in followups:
        followups_by_time[followup.VISIT_TIME] = followup
    
    logger.info(f"Found {followups.count()} follow-ups for {subjectid}")
    logger.info(f"Followups by time: {list(followups_by_time.keys())}")
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'followups_by_time': followups_by_time,  # Dict for template {% with followup=followups_by_time.day_14 %}
        'total_followups': followups.count(),
    }
    
    return render(request, 'studies/study_44en/CRF/individual/followup_list.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('individual_followup')
def individual_followup_create(request, subjectid):
    """
    CREATE new follow-up visit
    
    No audit log for CREATE (following project rules)
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL FOLLOW-UP CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # POST - Create new follow-up
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
        try:
            with transaction.atomic(using='db_study_44en'):
                logger.info("📝 Saving follow-up data...")
                
                # Create follow-up record
                followup = Individual_FollowUp(MEMBERID=individual)
                
                # Save VISIT_TIME
                visit_time = request.POST.get('VISIT_TIME', '').strip()
                if visit_time:
                    followup.VISIT_TIME = visit_time
                
                # Save ASSESSED Yes/No
                assessed = request.POST.get('ASSESSED', '').strip()
                if assessed:
                    followup.ASSESSED = assessed
                
                # Handle ASSESSMENT_DATE based on ASSESSED value
                if assessed == 'yes':
                    assessment_date_str = request.POST.get('ASSESSMENT_DATE', '').strip()
                    if not assessment_date_str:
                        raise ValueError('Assessment date is required when participant is assessed')
                    # Parse date string to date object
                    assessment_date = parse_date_string(assessment_date_str)
                    if not assessment_date:
                        raise ValueError(f'Invalid date format: {assessment_date_str}. Use dd/mm/yyyy format.')
                    followup.ASSESSMENT_DATE = assessment_date
                else:
                    # Clear assessment date if not assessed
                    followup.ASSESSMENT_DATE = None
                
                set_audit_metadata(followup, request.user)
                followup.save()
                logger.info(f"Created follow-up {followup.FUID} for {subjectid}")
                
                # Save symptoms using helper
                save_symptoms(request, followup)
                
                # Save hospitalizations using helper
                save_followup_hospitalizations(request, followup)
                
                # Save medications using helper
                save_followup_medications(request, followup)
                
                logger.info("=" * 80)
                logger.info("=== FOLLOW-UP CREATE SUCCESS ===")
                logger.info("=" * 80)
                
                messages.success(request, f'Follow-up visit created successfully')
                return redirect('study_44en:individual:followup_list', subjectid=subjectid)
                
        except Exception as e:
            logger.error(f"❌ Error creating follow-up: {e}", exc_info=True)
            messages.error(request, f'Error saving follow-up: {str(e)}')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
    
    # Get visit_time from query parameter if provided (from Create button on list)
    visit_time_param = request.GET.get('visit_time', '')
    
    # Load existing data (empty for create)
    symptom_data = {}
    hospitalization_data = {}
    medication_data = {}
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'symptom_data': symptom_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
        'visit_time_param': visit_time_param,  # Pre-fill VISIT_TIME dropdown
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info(f"=== 🌱 FOLLOW-UP CREATE END - Visit time param: {visit_time_param} ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/followup_form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
@require_crf_change('individual_followup')
@audit_log(model_name='Individual_FollowUp', get_patient_id_from='subjectid')
def individual_followup_update(request, subjectid, followup_id):
    """
    UPDATE existing follow-up visit
    
    MANUAL AUDIT handling for flat fields (following exposure pattern)
    
    Flow:
    1. Capture old data BEFORE form
    2. Detect changes (form fields + flat fields)
    3. Collect and validate reasons
    4. Save with audit
    """
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL FOLLOW-UP UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, FU ID: {followup_id}, Method: {request.method}")
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get follow-up (must exist for update)
    followup = get_object_or_404(
        Individual_FollowUp,
        FUID=followup_id,
        MEMBERID=individual
    )
    logger.info(f"Found follow-up {followup_id}")
    
    # GET - Show form with existing data
    if request.method == 'GET':
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        # Load existing data using helpers
        symptom_data = load_symptoms(followup)
        hospitalization_data = load_followup_hospitalizations(followup)
        medication_data = load_followup_medications(followup)
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'followup': followup,
            'symptom_data': symptom_data,
            'hospitalization_data': hospitalization_data,
            'medication_data': medication_data,
            'is_create': False,
            'is_readonly': False,
        }
        
        return render(request, 'studies/study_44en/CRF/individual/followup_form.html', context)
    
    # POST - Manual audit handling
    logger.info("POST - Manual audit handling")
    
    # IMPORTANT: Refresh followup from database to get latest values
    followup.refresh_from_db()
    logger.info(f"Refreshed followup from DB: HAS_SYMPTOMS={followup.HAS_SYMPTOMS}, HOSPITALIZED={followup.HOSPITALIZED}")
    
    # ===================================
    # STEP 1: Detect ALL changes
    # ===================================
    validator = ReasonValidator()
    
    all_changes = []
    
    # Form field changes (VISIT_TIME, ASSESSED, ASSESSMENT_DATE)
    form_changes = detect_followup_form_field_changes(request, followup)
    all_changes.extend(form_changes)
    logger.info(f"📝 Form field changes: {len(form_changes)}")
    
    # Flat field changes (symptoms, hospitalizations, medications)
    flat_changes = detect_followup_flat_field_changes(request, followup)
    all_changes.extend(flat_changes)
    logger.info(f"📝 Flat field changes: {len(flat_changes)}")
    
    # Filter out changes where values are actually the same after normalization
    def normalize_for_compare(val):
        """Normalize value for comparison - handle None, empty, lowercase"""
        if val is None:
            return ''
        if isinstance(val, bool):
            return 'true' if val else 'false'
        s = str(val).strip().lower()
        if s in ['(trống)', 'none', 'null', '']:
            return ''
        return s
    
    filtered_changes = []
    for c in all_changes:
        old_norm = normalize_for_compare(c.get('old_value', ''))
        new_norm = normalize_for_compare(c.get('new_value', ''))
        
        # Only keep if actually different
        if old_norm != new_norm:
            filtered_changes.append(c)
        else:
            logger.info(f"   ⏭️ Skipping {c['field']}: '{old_norm}' == '{new_norm}' (same after normalize)")
    
    all_changes = filtered_changes
    logger.info(f"📝 TOTAL changes (after normalize filter): {len(all_changes)}")
    
    # ===================================
    # STEP 2: No changes → save directly
    # ===================================
    if not all_changes:
        try:
            with transaction.atomic(using='db_study_44en'):
                logger.info("📝 No changes detected - saving directly without audit...")
                
                # Update VISIT_TIME
                visit_time = request.POST.get('VISIT_TIME', '').strip()
                if visit_time:
                    followup.VISIT_TIME = visit_time
                
                # Update ASSESSED Yes/No
                assessed = request.POST.get('ASSESSED', '').strip()
                if assessed:
                    followup.ASSESSED = assessed
                
                # Handle ASSESSMENT_DATE based on ASSESSED value
                if assessed == 'yes':
                    assessment_date_str = request.POST.get('ASSESSMENT_DATE', '').strip()
                    if assessment_date_str:
                        assessment_date = parse_date_string(assessment_date_str)
                        if assessment_date:
                            followup.ASSESSMENT_DATE = assessment_date
                else:
                    followup.ASSESSMENT_DATE = None
                
                set_audit_metadata(followup, request.user)
                followup.save()
                
                # Update related data
                save_symptoms(request, followup)
                save_followup_hospitalizations(request, followup)
                save_followup_medications(request, followup)
                
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:individual:followup_list', subjectid=subjectid)
        except Exception as e:
            logger.error(f"❌ Save failed: {e}", exc_info=True)
            messages.error(request, f'Error: {str(e)}')
    
    # ===================================
    # STEP 3: Has changes → collect reasons
    # ===================================
    reasons_data = {}
    for change in all_changes:
        reason_key = f'reason_{change["field"]}'
        reason = request.POST.get(reason_key, '').strip()
        if reason:
            reasons_data[change['field']] = reason
    
    # ===================================
    # STEP 4: Validate reasons
    # ===================================
    required_fields = [c['field'] for c in all_changes]
    validation_result = validator.validate_reasons(reasons_data, required_fields)
    
    if not validation_result['valid']:
        # Show reason modal - preserve POST data
        messages.warning(request, 'Vui lòng cung cấp lý do cho tất cả các thay đổi')
        
        # Preserve symptom data from POST
        symptom_data = {'has_symptoms': request.POST.get('has_symptoms', '')}
        for symptom_key in ['fatigue', 'fever', 'cough', 'eye_pain', 'red_eye', 'muscle_pain',
                           'anorexia', 'dyspnea', 'jaundice', 'headache', 'dysuria', 'hematuria',
                           'difficult_urination', 'cloudy_urine', 'vomiting', 'nausea', 'diarrhea',
                           'abdominal_pain', 'other']:
            symptom_data[f'symptom_{symptom_key}'] = request.POST.get(f'symptom_{symptom_key}') == 'on'
        symptom_data['symptom_other_text'] = request.POST.get('symptom_other_text', '')
        
        # Preserve hospitalization data from POST
        hospitalization_data = {'hospitalized_since': request.POST.get('hospitalized_since', '')}
        for hosp_key in ['central', 'city', 'district', 'private', 'other']:
            hospitalization_data[f'fu_hosp_{hosp_key}'] = request.POST.get(f'fu_hosp_{hosp_key}') == 'on'
            hospitalization_data[f'fu_hosp_{hosp_key}_duration'] = request.POST.get(f'fu_hosp_{hosp_key}_duration', '')
        hospitalization_data['fu_hosp_other_text'] = request.POST.get('fu_hosp_other_text', '')
        
        # Preserve medication data from POST
        medication_data = {'medication_since': request.POST.get('medication_since', '')}
        medication_data['med_antibiotics_fu'] = request.POST.get('med_antibiotics_fu') == 'on'
        medication_data['med_antibiotics_type'] = request.POST.get('med_antibiotics_type', '')
        medication_data['med_steroids_fu'] = request.POST.get('med_steroids_fu') == 'on'
        medication_data['med_steroids_type'] = request.POST.get('med_steroids_type', '')
        medication_data['med_other_fu'] = request.POST.get('med_other_fu') == 'on'
        medication_data['med_other_type'] = request.POST.get('med_other_type', '')
        
        cancel_url = reverse('study_44en:individual:followup_list', kwargs={'subjectid': subjectid})
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'followup': followup,
            'symptom_data': symptom_data,
            'hospitalization_data': hospitalization_data,
            'medication_data': medication_data,
            'is_create': False,
            'is_readonly': False,
            'detected_changes': all_changes,
            'show_reason_form': True,
            'submitted_reasons': reasons_data,
            'cancel_url': cancel_url,
            'edit_post_data': request.POST,
        }
        return render(request, 'studies/study_44en/CRF/individual/followup_form.html', context)
    
    # ===================================
    # STEP 5: Save with audit
    # ===================================
    sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
    
    # Set audit_data for decorator
    combined_reason = "\n".join([
        f"{change['field']}: {sanitized_reasons.get(change['field'], 'N/A')}"
        for change in all_changes
    ])
    
    request.audit_data = {
        'patient_id': subjectid,
        'site_id': getattr(individual, 'SITEID', None),
        'reason': combined_reason,
        'changes': all_changes,
        'reasons_json': sanitized_reasons,
    }
    
    try:
        with transaction.atomic(using='db_study_44en'):
            logger.info("📝 Saving with audit...")
            
            # Update VISIT_TIME
            visit_time = request.POST.get('VISIT_TIME', '').strip()
            if visit_time:
                followup.VISIT_TIME = visit_time
            
            # Update ASSESSED Yes/No
            assessed = request.POST.get('ASSESSED', '').strip()
            if assessed:
                followup.ASSESSED = assessed
            
            # Handle ASSESSMENT_DATE based on ASSESSED value
            if assessed == 'yes':
                assessment_date_str = request.POST.get('ASSESSMENT_DATE', '').strip()
                if assessment_date_str:
                    assessment_date = parse_date_string(assessment_date_str)
                    if assessment_date:
                        followup.ASSESSMENT_DATE = assessment_date
            else:
                followup.ASSESSMENT_DATE = None
            
            set_audit_metadata(followup, request.user)
            followup.save()
            logger.info(f"Updated follow-up {followup.FUID}")
            
            # Update related data using helpers
            save_symptoms(request, followup)
            save_followup_hospitalizations(request, followup)
            save_followup_medications(request, followup)
            
            logger.info("=" * 80)
            logger.info(f"=== FOLLOW-UP UPDATE SUCCESS WITH AUDIT: {subjectid} ===")
            logger.info("=" * 80)
            
            messages.success(request, f'Cập nhật thành công follow-up cho {subjectid}!')
            return redirect('study_44en:individual:followup_list', subjectid=subjectid)
            
    except Exception as e:
        logger.error(f"❌ Error updating follow-up: {e}", exc_info=True)
        messages.error(request, f'Error updating follow-up: {str(e)}')
    
    # Re-render with errors
    symptom_data = load_symptoms(followup)
    hospitalization_data = load_followup_hospitalizations(followup)
    medication_data = load_followup_medications(followup)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'followup': followup,
        'symptom_data': symptom_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
        'is_create': False,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 📝 FOLLOW-UP UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/followup_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('individual_followup')
def individual_followup_view(request, subjectid, followup_id):
    """
    VIEW follow-up visit (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL FOLLOW-UP VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get follow-up by FUID (primary key)
    followup = get_object_or_404(
        Individual_FollowUp,
        FUID=followup_id,
        MEMBERID=individual
    )
    
    # Load existing data using helpers
    symptom_data = load_symptoms(followup)
    hospitalization_data = load_followup_hospitalizations(followup)
    medication_data = load_followup_medications(followup)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'followup': followup,
        'symptom_data': symptom_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("=" * 80)
    logger.info("=== 👁️ FOLLOW-UP VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/followup_form.html', context)


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
def individual_followup_detail(request, subjectid, followup_id):
    """
    DEPRECATED: Legacy view that handled both view and update
    Redirects to update view
    
    This is kept for backward compatibility with old URLs
    """
    logger.warning(f"⚠️ Using deprecated 'individual_followup_detail' - redirecting to 'individual_followup_update'")
    return individual_followup_update(request, subjectid, followup_id)


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'individual_followup_list',
    'individual_followup_create',
    'individual_followup_update',   # With audit log support
    'individual_followup_view',      # Read-only
    'individual_followup_detail',    # Deprecated alias
]