# backends/api/studies/study_44en/views/individual/views_individual_sample.py

"""
Individual Sample Views for Study 44EN
Handles sample collection (4 visit times) and food frequency data

REFACTORED: Full Audit Log Support (following exposure/followup pattern)
- Manual change detection for flat fields
- Reason modal workflow
- Audit log creation via decorator
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.individual import (
    Individual, Individual_Sample, Individual_FoodFrequency
)
from backends.studies.study_44en.forms.individual import Individual_FoodFrequencyForm
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals
from backends.studies.study_44en.models import AuditLog, AuditLogDetail

# Import audit utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.detector import ChangeDetector
from backends.audit_logs.utils.validator import ReasonValidator

# Import sample helpers with change detection
from .helpers_sample import (
    set_audit_metadata,
    make_form_readonly,
    save_samples,
    load_samples,
    # NEW: Change detection for audit log
    detect_sample_flat_field_changes,
    detect_food_frequency_form_changes,
)

from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    require_crf_delete,
)


logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('individual_sample')
def individual_sample_create(request, subjectid):
    """
    CREATE new sample and food frequency data
    
    No audit log for CREATE (following project rules)
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL SAMPLE CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check if sample data already exists
    sample_exists = Individual_Sample.objects.filter(MEMBERID=individual).exists()
    food_exists = Individual_FoodFrequency.objects.filter(MEMBERID=individual).exists()
    
    if sample_exists or food_exists:
        logger.warning(f"⚠️ Sample data already exists for {subjectid} - redirecting to update")
        messages.warning(
            request,
            f'Sample data already exists for individual {subjectid}. Redirecting to update.'
        )
        return redirect('study_44en:individual:sample_update', subjectid=subjectid)
    
    # POST - Create new sample data
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info(" POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
        food_frequency_form = Individual_FoodFrequencyForm(
            request.POST,
            prefix='food'
        )
        
        if food_frequency_form.is_valid():
            try:
                with transaction.atomic(using='db_study_44en'):
                    logger.info(" Saving sample data...")
                    
                    # Save samples using helper (handles 4 visit times)
                    save_samples(request, individual)
                    
                    # Save food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.MEMBERID = individual
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"Created food frequency for {subjectid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== SAMPLE CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(request, f'Created sample data for individual {subjectid}')
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f" Error creating sample data: {e}", exc_info=True)
                messages.error(request, f'Error creating sample data: {str(e)}')
        else:
            logger.error(" Form validation failed")
            logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            messages.error(request, ' Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        food_frequency_form = Individual_FoodFrequencyForm(prefix='food')
    
    # Load empty sample data
    sample_data = {}
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'sample_data': sample_data,
        'food_frequency_form': food_frequency_form,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 🌱 SAMPLE CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
@require_crf_change('individual_sample')
@audit_log(
    model_name='Individual_Sample',
    get_patient_id_from='subjectid',
    patient_model=Individual,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def individual_sample_update(request, subjectid):
    """
    UPDATE existing sample and food frequency data
    
    MANUAL AUDIT handling for flat fields (following exposure/followup pattern)
    
    Flow:
    1. Capture old data BEFORE form
    2. Detect changes (form fields + flat fields)
    3. Collect and validate reasons
    4. Save with audit
    """
    logger.info("=" * 80)
    logger.info("===  INDIVIDUAL SAMPLE UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get food frequency (may or may not exist)
    try:
        food_frequency = Individual_FoodFrequency.objects.get(MEMBERID=individual)
        logger.info(f"Found food frequency for {subjectid}")
    except Individual_FoodFrequency.DoesNotExist:
        logger.warning(f"⚠️ No food frequency found for {subjectid}")
        food_frequency = None
    
    # GET - Show form with existing data
    if request.method == 'GET':
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        food_frequency_form = Individual_FoodFrequencyForm(
            instance=food_frequency,
            prefix='food'
        )
        
        # Load existing sample data using helper
        sample_data = load_samples(individual)
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'sample_data': sample_data,
            'food_frequency': food_frequency,
            'food_frequency_form': food_frequency_form,
            'is_create': False,
            'is_readonly': False,
        }
        
        return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)
    
    # POST - Manual audit handling
    logger.info("POST - Manual audit handling")
    
    # ===================================
    # STEP 1: Detect ALL changes
    # ===================================
    detector = ChangeDetector()
    validator = ReasonValidator()
    
    all_changes = []
    
    # Sample flat field changes (4 visit times x 4 fields each)
    sample_changes = detect_sample_flat_field_changes(request, individual)
    all_changes.extend(sample_changes)
    logger.info(f" Sample flat field changes: {len(sample_changes)}")
    
    # Food frequency form changes (if food_frequency exists)
    food_frequency_form = Individual_FoodFrequencyForm(
        request.POST,
        instance=food_frequency,
        prefix='food'
    )
    
    if food_frequency and food_frequency_form.is_valid():
        old_food_data = detector.extract_old_data(food_frequency)
        new_food_data = detector.extract_new_data(food_frequency_form)
        food_changes = detector.detect_changes(old_food_data, new_food_data)
        all_changes.extend(food_changes)
        logger.info(f" Food frequency form changes: {len(food_changes)}")
    elif food_frequency is None and food_frequency_form.is_valid():
        # Creating new food frequency - all fields are "new"
        logger.info(" Creating new food frequency - no changes to detect")
    
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
    logger.info(f" TOTAL changes (after normalize filter): {len(all_changes)}")
    
    # ===================================
    # STEP 2: No changes → save directly
    # ===================================
    if not all_changes:
        if food_frequency_form.is_valid():
            try:
                with transaction.atomic(using='db_study_44en'):
                    logger.info(" No changes detected - saving directly without audit...")
                    
                    # Update samples using helper (handles 4 visit times)
                    save_samples(request, individual)
                    
                    # Update food frequency
                    food_freq = food_frequency_form.save(commit=False)
                    food_freq.MEMBERID = individual
                    set_audit_metadata(food_freq, request.user)
                    food_freq.save()
                    
                    messages.success(request, 'Lưu thành công!')
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
            except Exception as e:
                logger.error(f" Save failed: {e}", exc_info=True)
                messages.error(request, f'Error: {str(e)}')
        else:
            logger.error(" Form validation failed")
            logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            messages.error(request, ' Please check the form for errors')
    
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
        
        # Preserve sample data from POST
        sample_data = {}
        for form_prefix in ['enrollment', 'day14', 'day28', 'day90']:
            sample_data[f'sample_{form_prefix}'] = request.POST.get(f'sample_{form_prefix}', '')
            sample_data[f'stool_date_{form_prefix}'] = request.POST.get(f'stool_date_{form_prefix}', '')
            sample_data[f'throat_date_{form_prefix}'] = request.POST.get(f'throat_date_{form_prefix}', '')
            sample_data[f'reason_{form_prefix}'] = request.POST.get(f'reason_{form_prefix}', '')
        
        cancel_url = reverse('study_44en:individual:detail', kwargs={'subjectid': subjectid})
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'sample_data': sample_data,
            'food_frequency': food_frequency,
            'food_frequency_form': food_frequency_form,
            'is_create': False,
            'is_readonly': False,
            'detected_changes': all_changes,
            'show_reason_form': True,
            'submitted_reasons': reasons_data,
            'cancel_url': cancel_url,
            'edit_post_data': request.POST,
        }
        return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)
    
    # ===================================
    # STEP 5: Save with audit
    # ===================================
    if not food_frequency_form.is_valid():
        logger.error(" Form validation failed")
        logger.error(f"Food frequency errors: {food_frequency_form.errors}")
        messages.error(request, ' Please check the form for errors')
        
        sample_data = load_samples(individual)
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'sample_data': sample_data,
            'food_frequency': food_frequency,
            'food_frequency_form': food_frequency_form,
            'is_create': False,
            'is_readonly': False,
        }
        return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)
    
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
            logger.info(" Saving with audit...")
            
            # Update samples using helper (handles 4 visit times)
            save_samples(request, individual)
            
            # Update food frequency
            food_freq = food_frequency_form.save(commit=False)
            food_freq.MEMBERID = individual
            set_audit_metadata(food_freq, request.user)
            food_freq.save()
            logger.info(f"Updated food frequency for {subjectid}")
            
            logger.info("=" * 80)
            logger.info(f"=== SAMPLE UPDATE SUCCESS WITH AUDIT: {subjectid} ===")
            logger.info("=" * 80)
            
            messages.success(request, f'Cập nhật thành công sample data cho {subjectid}!')
            return redirect('study_44en:individual:detail', subjectid=subjectid)
            
    except Exception as e:
        logger.error(f" Error updating sample data: {e}", exc_info=True)
        messages.error(request, f'Error updating sample data: {str(e)}')
    
    # Re-render with errors
    sample_data = load_samples(individual)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'sample_data': sample_data,
        'food_frequency': food_frequency,
        'food_frequency_form': food_frequency_form,
        'is_create': False,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("===  SAMPLE UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('individual_sample')
def individual_sample_view(request, subjectid):
    """
    VIEW sample data (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL SAMPLE VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get food frequency
    try:
        food_frequency = Individual_FoodFrequency.objects.get(MEMBERID=individual)
    except Individual_FoodFrequency.DoesNotExist:
        food_frequency = None
    
    # Load sample data using helper
    sample_data = load_samples(individual)
    
    # If no data exists, redirect to detail
    if not sample_data and food_frequency is None:
        messages.error(request, f'No sample data found for individual {subjectid}')
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    # Create readonly form for food frequency
    food_frequency_form = Individual_FoodFrequencyForm(
        instance=food_frequency,
        prefix='food'
    )
    make_form_readonly(food_frequency_form)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'sample_data': sample_data,
        'food_frequency': food_frequency,
        'food_frequency_form': food_frequency_form,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("=" * 80)
    logger.info("=== 👁️ SAMPLE VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
def individual_sample(request, subjectid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    
    This is kept for backward compatibility with old URLs
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check if sample data exists
    sample_exists = Individual_Sample.objects.filter(MEMBERID=individual).exists()
    food_exists = Individual_FoodFrequency.objects.filter(MEMBERID=individual).exists()
    
    if sample_exists or food_exists:
        # Data exists - redirect to update
        logger.info(f"Sample data exists for {subjectid} - redirecting to update")
        return redirect('study_44en:individual:sample_update', subjectid=subjectid)
    else:
        # No data - redirect to create
        logger.info(f"No sample data for {subjectid} - redirecting to create")
        return redirect('study_44en:individual:sample_create', subjectid=subjectid)


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'individual_sample_create',
    'individual_sample_update',   # With audit log support
    'individual_sample_view',      # Read-only
    'individual_sample',           # Deprecated but kept for compatibility
]
