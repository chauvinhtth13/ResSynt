"""
Individual Exposure Views for Study 44EN
Handles exposure, comorbidity, vaccine, hospitalization, medication, and travel data

✅ REFACTORED: Full Audit Log Support (following household pattern)
- Manual change detection for flat fields
- Reason modal workflow
- Audit log creation via decorator

Architecture:
- EXP 1/3: Water sources, treatments, comorbidities
- EXP 2/3: Vaccination, hospitalization, medication
- EXP 3/3: Food frequency, travel history
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.individual import Individual, Individual_Exposure
from backends.studies.study_44en.forms.individual import Individual_ExposureForm, Individual_Exposure2Form
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals

# ✅ Import audit utilities
from backends.audit_log.utils.decorators import audit_log
from backends.audit_log.utils.detector import ChangeDetector
from backends.audit_log.utils.validator import ReasonValidator

# ✅ Import exposure helpers with change detection
from .helpers_exposure import (
    # Utility functions
    set_audit_metadata,
    make_form_readonly,
    
    # EXP 1/3 - Save/Load
    save_water_sources,
    save_water_treatment,
    save_comorbidities,
    load_water_data,
    load_treatment_data,
    load_comorbidity_data,
    
    # EXP 2/3 - Save/Load
    save_vaccines,
    save_hospitalizations,
    save_medications,
    load_vaccines,
    load_hospitalizations,
    load_medications,
    
    # EXP 3/3 - Save/Load
    save_food_frequency,
    save_travel_history,
    load_food_frequency,
    load_travel_history,
    
    # ✅ NEW: Change detection for audit log
    detect_exp1_flat_field_changes,
    detect_exp2_flat_field_changes,
    detect_exp3_flat_field_changes,
)

# Import permission decorators
from backends.studies.study_44en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    require_crf_delete,
)

logger = logging.getLogger(__name__)


# ==========================================
# EXPOSURE 1/3 - WATER & COMORBIDITIES
# ==========================================

@login_required
@require_crf_add('individual_exposure')
def individual_exposure_create(request, subjectid):
    """CREATE new exposure data (water sources, treatment, comorbidities)
    
    ✅ No audit log for CREATE (following project rules)
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL EXPOSURE CREATE START ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    logger.info("=" * 80)
    
    # Get individual
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check if already exists
    if Individual_Exposure.objects.filter(MEMBERID=individual).exists():
        logger.warning(f"Exposure already exists for {subjectid}")
        messages.warning(request, f'Exposure data already exists for {subjectid}. Redirecting to update.')
        return redirect('study_44en:individual:exposure_update', subjectid=subjectid)
    
    # GET - Show blank form
    if request.method == 'GET':
        exposure_form = Individual_ExposureForm()
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'exposure_form': exposure_form,
            'is_create': True,
            'is_readonly': False,
            'water_data': {},
            'treatment_data': {},
            'comorbidity_data': {},
            'shared_toilet': None,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)
    
    # POST - Process creation
    logger.info("Processing POST - Creating exposure")
    
    exposure_form = Individual_ExposureForm(request.POST)
    
    if exposure_form.is_valid():
        try:
            with transaction.atomic(using='db_study_44en'):
                # Save main exposure
                exposure = exposure_form.save(commit=False)
                exposure.MEMBERID = individual
                
                # Handle hardcoded radio buttons not in form
                shared_toilet = request.POST.get('shared_toilet', '').strip()
                if shared_toilet:
                    exposure.SHARED_TOILET = shared_toilet
                
                water_treatment = request.POST.get('water_treatment', '').strip()
                if water_treatment:
                    exposure.WATER_TREATMENT = water_treatment
                
                has_conditions = request.POST.get('has_conditions', '').strip()
                if has_conditions:
                    exposure.HAS_COMORBIDITY = has_conditions
                
                set_audit_metadata(exposure, request.user)
                if hasattr(exposure, 'version'):
                    exposure.version = 0
                exposure.save()
                logger.info(f"Created exposure for {subjectid}")
                
                # Save related data using helper functions
                save_water_sources(request, exposure)
                save_water_treatment(request, exposure)
                save_comorbidities(request, exposure)
                
                logger.info("=== ✅ EXPOSURE CREATE SUCCESS ===")
                messages.success(request, f'Created exposure data for {subjectid}')
                return redirect('study_44en:individual:detail', subjectid=subjectid)
                
        except Exception as e:
            logger.error(f"❌ Error creating exposure: {e}", exc_info=True)
            messages.error(request, f'Error creating exposure: {str(e)}')
    else:
        logger.error(f"Form validation failed: {exposure_form.errors}")
        messages.error(request, '❌ Please check the form for errors')
    
    # Re-render with errors - preserve POST data
    water_data = {}
    for source_key in ['tap', 'bottle', 'well', 'rain', 'river', 'pond', 'other']:
        water_data[f'water_{source_key}_drink'] = request.POST.get(f'water_{source_key}_drink') == 'on'
        water_data[f'water_{source_key}_domestic'] = request.POST.get(f'water_{source_key}_domestic') == 'on'
        water_data[f'water_{source_key}_irrigation'] = request.POST.get(f'water_{source_key}_irrigation') == 'on'
        water_data[f'water_{source_key}_other'] = request.POST.get(f'water_{source_key}_other', '')
    water_data['water_other_src_name'] = request.POST.get('water_other_src_name', '')
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure_form': exposure_form,
        'is_create': True,
        'is_readonly': False,
        'water_data': water_data,
        'treatment_data': {},
        'comorbidity_data': {},
        'shared_toilet': request.POST.get('shared_toilet', ''),
    }
    
    logger.info("=== 🌱 EXPOSURE CREATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)


@login_required
@require_crf_change('individual_exposure')
@audit_log(model_name='Individual_Exposure', get_patient_id_from='subjectid')
def individual_exposure_update(request, subjectid):
    """UPDATE existing exposure data
    
    ✅ MANUAL AUDIT handling for flat fields (following household pattern)
    
    Flow:
    1. Capture old data BEFORE form
    2. Detect changes (form + flat fields)
    3. Collect and validate reasons
    4. Save with audit
    """
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL EXPOSURE UPDATE START ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    logger.info("=" * 80)
    
    # Get individual and exposure
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    try:
        exposure = Individual_Exposure.objects.get(MEMBERID=individual)
        logger.info(f"Found existing exposure for {subjectid}")
    except Individual_Exposure.DoesNotExist:
        logger.warning(f"No exposure found for {subjectid}")
        messages.error(request, f'No exposure data found for {subjectid}. Please create first.')
        return redirect('study_44en:individual:exposure_create', subjectid=subjectid)
    
    # GET - Show form with existing data
    if request.method == 'GET':
        logger.info("GET request - Loading existing data")
        exposure_form = Individual_ExposureForm(instance=exposure)
        
        water_data = load_water_data(exposure)
        treatment_data = load_treatment_data(exposure)
        comorbidity_data = load_comorbidity_data(exposure)
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'is_create': False,
            'is_readonly': False,
            'water_data': water_data,
            'treatment_data': treatment_data,
            'comorbidity_data': comorbidity_data,
            # ✅ FIX: Normalize to lowercase for template comparison
            'shared_toilet': (exposure.SHARED_TOILET or '').lower() if exposure.SHARED_TOILET else '',
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)
    
    # ✅ POST - Manual audit handling
    logger.info("🔄 POST - Manual audit handling")
    
    # ✅ IMPORTANT: Refresh exposure from database to get latest values
    exposure.refresh_from_db()
    logger.info(f"🔄 Refreshed exposure from DB: SHARED_TOILET={exposure.SHARED_TOILET}")
    
    # DEBUG: Log POST data
    logger.info("=" * 80)
    logger.info("📦 POST DATA DEBUG:")
    for key, value in request.POST.items():
        if key.startswith(('water_', 'treatment_', 'condition_', 'shared_', 'has_')):
            logger.info(f"  {key}: '{value}'")
    logger.info("=" * 80)
    
    # ===================================
    # STEP 1: Detect ALL changes
    # ===================================
    detector = ChangeDetector()
    validator = ReasonValidator()
    
    # Form changes
    old_form_data = detector.extract_old_data(exposure)
    exposure_form = Individual_ExposureForm(request.POST, instance=exposure)
    
    all_changes = []
    
    # ✅ Fields that are handled by flat field detection (hardcoded HTML, not in Django form)
    # These will be detected by detect_exp1_flat_field_changes() instead
    # Include ALL possible variations of field names
    flat_field_names = {
        # Model field names (uppercase)
        'SHARED_TOILET', 'WATER_TREATMENT', 'HAS_COMORBIDITY',
        # HTML field names (lowercase)
        'shared_toilet', 'water_treatment', 'has_conditions',
    }
    
    if exposure_form.is_valid():
        new_form_data = detector.extract_new_data(exposure_form)
        form_changes = detector.detect_changes(old_form_data, new_form_data)
        
        # ✅ DEBUG: Log all form changes before filter
        logger.info("📝 Form changes BEFORE filter:")
        for c in form_changes:
            logger.info(f"   - {c['field']}: '{c.get('old_value')}' → '{c.get('new_value')}'")
        
        # ✅ Filter out fields that are handled by flat field detection
        # Use case-insensitive comparison
        form_changes = [c for c in form_changes 
                       if c['field'] not in flat_field_names 
                       and c['field'].upper() not in flat_field_names
                       and c['field'].lower() not in flat_field_names]
        
        logger.info(f"📝 Form changes AFTER filter: {len(form_changes)}")
        all_changes.extend(form_changes)
    
    # Flat field changes (water, treatment, comorbidities + radio buttons)
    flat_changes = detect_exp1_flat_field_changes(request, exposure)
    
    # ✅ DEBUG: Log flat changes
    logger.info("📝 Flat changes detected:")
    for c in flat_changes:
        logger.info(f"   - {c['field']}: '{c.get('old_value')}' → '{c.get('new_value')}'")
    
    all_changes.extend(flat_changes)
    logger.info(f"📝 Total before final filter: {len(all_changes)}")
    
    # ✅ IMPROVED: Filter out changes where values are actually the same
    # Normalize both values for comparison
    def normalize_for_compare(val):
        """Normalize value for comparison - handle None, empty, lowercase"""
        if val is None:
            return ''
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
                exposure = exposure_form.save(commit=False)
                
                # Handle hardcoded radio buttons
                shared_toilet = request.POST.get('shared_toilet', '').strip()
                if shared_toilet:
                    exposure.SHARED_TOILET = shared_toilet
                
                water_treatment = request.POST.get('water_treatment', '').strip()
                if water_treatment:
                    exposure.WATER_TREATMENT = water_treatment
                
                has_conditions = request.POST.get('has_conditions', '').strip()
                if has_conditions:
                    exposure.HAS_COMORBIDITY = has_conditions
                
                set_audit_metadata(exposure, request.user)
                exposure.save()
                
                save_water_sources(request, exposure)
                save_water_treatment(request, exposure)
                save_comorbidities(request, exposure)
                
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
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
        
        # Preserve water source values from POST
        water_data = {}
        for source_key in ['tap', 'bottle', 'well', 'rain', 'river', 'pond', 'other']:
            water_data[f'water_{source_key}_drink'] = request.POST.get(f'water_{source_key}_drink') == 'on'
            water_data[f'water_{source_key}_domestic'] = request.POST.get(f'water_{source_key}_domestic') == 'on'
            water_data[f'water_{source_key}_irrigation'] = request.POST.get(f'water_{source_key}_irrigation') == 'on'
            water_data[f'water_{source_key}_other'] = request.POST.get(f'water_{source_key}_other', '')
        water_data['water_other_src_name'] = request.POST.get('water_other_src_name', '')
        
        # Preserve treatment data from POST
        treatment_data = {}
        for treatment_key in ['boil', 'filter', 'pitcher', 'chemical', 'sodis', 'other']:
            treatment_data[f'treatment_{treatment_key}'] = request.POST.get(f'treatment_{treatment_key}') == 'on'
        treatment_data['treatment_other_text'] = request.POST.get('treatment_other_text', '')
        treatment_data['water_treatment'] = request.POST.get('water_treatment', '')
        
        # Preserve comorbidity data from POST
        comorbidity_data = {}
        for condition_key in ['hypertension', 'diabetes', 'heart', 'kidney', 'liver', 'asthma', 'cancer', 'other']:
            comorbidity_data[f'condition_{condition_key}'] = request.POST.get(f'condition_{condition_key}') == 'on'
            comorbidity_data[f'condition_{condition_key}_treated'] = request.POST.get(f'condition_{condition_key}_treated', '')
        comorbidity_data['condition_other_text'] = request.POST.get('condition_other_text', '')
        comorbidity_data['has_conditions'] = request.POST.get('has_conditions', '')
        
        cancel_url = reverse('study_44en:individual:detail', kwargs={'subjectid': subjectid})
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'is_create': False,
            'is_readonly': False,
            'water_data': water_data,
            'treatment_data': treatment_data,
            'comorbidity_data': comorbidity_data,
            'shared_toilet': request.POST.get('shared_toilet', ''),
            'detected_changes': all_changes,
            'show_reason_form': True,
            'submitted_reasons': reasons_data,
            'cancel_url': cancel_url,
            'edit_post_data': request.POST,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)
    
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
            # 1. Save main exposure form
            exposure = exposure_form.save(commit=False)
            
            # Handle hardcoded radio buttons
            shared_toilet = request.POST.get('shared_toilet', '').strip()
            if shared_toilet:
                exposure.SHARED_TOILET = shared_toilet
            
            water_treatment = request.POST.get('water_treatment', '').strip()
            if water_treatment:
                exposure.WATER_TREATMENT = water_treatment
            
            has_conditions = request.POST.get('has_conditions', '').strip()
            if has_conditions:
                exposure.HAS_COMORBIDITY = has_conditions
            
            set_audit_metadata(exposure, request.user)
            exposure.save()
            logger.info(f"✅ Saved exposure for {subjectid}")
            
            # 2. Save related data
            save_water_sources(request, exposure)
            save_water_treatment(request, exposure)
            save_comorbidities(request, exposure)
            
            logger.info("=" * 80)
            logger.info(f"=== ✅ UPDATE SUCCESS WITH AUDIT: {subjectid} ===")
            logger.info("=" * 80)
            
            messages.success(request, f'Cập nhật thành công exposure cho {subjectid}!')
            return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
    except Exception as e:
        logger.error(f"❌ Save failed: {e}", exc_info=True)
        messages.error(request, f'Error: {str(e)}')
    
    # Re-render with errors
    water_data = load_water_data(exposure)
    treatment_data = load_treatment_data(exposure)
    comorbidity_data = load_comorbidity_data(exposure)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'is_create': False,
        'is_readonly': False,
        'water_data': water_data,
        'treatment_data': treatment_data,
        'comorbidity_data': comorbidity_data,
        'shared_toilet': exposure.SHARED_TOILET,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)


@login_required
@require_crf_view('individual_exposure')
def individual_exposure_view(request, subjectid):
    """VIEW exposure data (read-only)"""
    logger.info("=== 👁️ INDIVIDUAL EXPOSURE VIEW (READ-ONLY) ===")
    
    # Get individual and exposure
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    try:
        exposure = Individual_Exposure.objects.get(MEMBERID=individual)
    except Individual_Exposure.DoesNotExist:
        messages.error(request, f'No exposure data found for {subjectid}')
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    # Create readonly form
    exposure_form = Individual_ExposureForm(instance=exposure)
    make_form_readonly(exposure_form)
    
    # Load existing data
    water_data = load_water_data(exposure)
    treatment_data = load_treatment_data(exposure)
    comorbidity_data = load_comorbidity_data(exposure)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'is_create': False,
        'is_readonly': True,
        'water_data': water_data,
        'treatment_data': treatment_data,
        'comorbidity_data': comorbidity_data,
        'shared_toilet': exposure.SHARED_TOILET,
    }
    
    logger.info("=== 👁️ EXPOSURE VIEW END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)


# ==========================================
# EXPOSURE 2/3 - VACCINATION & HOSPITALIZATION
# ==========================================

@login_required
def individual_exposure_2_create(request, subjectid):
    """CREATE exposure 2 (vaccination & hospitalization)
    
    ✅ No audit log for CREATE
    """
    logger.info("=" * 80)
    logger.info("=== 💉 EXPOSURE 2 CREATE (VACCINATION & HOSPITALIZATION) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check if already exists
    if Individual_Exposure.objects.filter(MEMBERID=individual).exists():
        logger.warning(f"Exposure already exists for {subjectid}")
        messages.warning(request, f'Exposure data already exists for {subjectid}. Redirecting to update.')
        return redirect('study_44en:individual:exposure_2_update', subjectid=subjectid)
    
    # GET - Show blank form
    if request.method == 'GET':
        exposure_form = Individual_Exposure2Form()
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'exposure_form': exposure_form,
            'is_create': True,
            'is_readonly': False,
            'vaccine_data': {},
            'hospitalization_data': {},
            'medication_data': {},
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)
    
    # POST
    logger.info("Processing POST - Creating exposure 2")
    
    exposure_form = Individual_Exposure2Form(request.POST)
    
    if exposure_form.is_valid():
        try:
            with transaction.atomic(using='db_study_44en'):
                # Create new exposure with only EXP 2/3 data
                exposure = Individual_Exposure(MEMBERID=individual)
                
                # ✅ FIX: Don't save raw values directly - let helper functions handle mapping
                # exposure.VACCINATION_STATUS, HOSPITALIZED_3M, MEDICATION_3M will be set by helpers
                
                set_audit_metadata(exposure, request.user)
                if hasattr(exposure, 'version'):
                    exposure.version = 0
                exposure.save()
                logger.info(f"Created exposure for {subjectid}")
                
                # Save related data (helper functions will set the status fields with proper mapping)
                save_vaccines(request, exposure)
                save_hospitalizations(request, exposure)
                save_medications(request, exposure)
                
                logger.info("=== ✅ EXPOSURE 2 CREATE SUCCESS ===")
                messages.success(request, f'Created exposure 2 data for {subjectid}')
                return redirect('study_44en:individual:detail', subjectid=subjectid)
                
        except Exception as e:
            logger.error(f"❌ Error creating exposure 2: {e}", exc_info=True)
            messages.error(request, f'Error creating exposure 2: {str(e)}')
    else:
        logger.error(f"Form validation failed: {exposure_form.errors}")
        messages.error(request, '❌ Please check the form for errors')
    
    # Re-render with errors
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure_form': exposure_form,
        'is_create': True,
        'is_readonly': False,
        'vaccine_data': {},
        'hospitalization_data': {},
        'medication_data': {},
    }
    
    logger.info("=== 💉 EXPOSURE 2 CREATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


@login_required
@audit_log(model_name='Individual_Exposure', get_patient_id_from='subjectid')
def individual_exposure_2_update(request, subjectid):
    """UPDATE exposure 2 (vaccination & hospitalization)
    
    ✅ MANUAL AUDIT handling for flat fields
    """
    logger.info("=" * 80)
    logger.info("=== ✏️ EXPOSURE 2 UPDATE (VACCINATION & HOSPITALIZATION) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get exposure
    try:
        exposure = Individual_Exposure.objects.get(MEMBERID=individual)
    except Individual_Exposure.DoesNotExist:
        logger.error(f"No exposure found for {subjectid}")
        messages.error(request, f'No exposure data found for {subjectid}. Please create first.')
        return redirect('study_44en:individual:exposure_2_create', subjectid=subjectid)
    
    # GET - Show form with existing data
    if request.method == 'GET':
        logger.info("GET request - Loading existing data")
        exposure_form = Individual_Exposure2Form(instance=exposure)
        
        vaccine_data = load_vaccines(exposure)
        hospitalization_data = load_hospitalizations(exposure)
        medication_data = load_medications(exposure)
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'is_create': False,
            'is_readonly': False,
            'vaccine_data': vaccine_data,
            'hospitalization_data': hospitalization_data,
            'medication_data': medication_data,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)
    
    # ✅ POST - Manual audit handling
    logger.info("🔄 POST - Manual audit handling")
    
    # ✅ IMPORTANT: Refresh exposure from database to get latest values
    exposure.refresh_from_db()
    logger.info(f"🔄 Refreshed exposure from DB: VACCINATION_STATUS={exposure.VACCINATION_STATUS}, HOSPITALIZED_3M={exposure.HOSPITALIZED_3M}, MEDICATION_3M={exposure.MEDICATION_3M}")
    
    # ===================================
    # STEP 1: Detect ALL changes
    # ===================================
    detector = ChangeDetector()
    validator = ReasonValidator()
    
    # Form changes
    old_form_data = detector.extract_old_data(exposure)
    exposure_form = Individual_Exposure2Form(request.POST, instance=exposure)
    
    all_changes = []
    
    # ✅ Fields that are handled by flat field detection (hardcoded HTML, not in Django form)
    flat_field_names = {
        'VACCINATION_STATUS', 'HOSPITALIZED_3M', 'MEDICATION_3M',
        'vaccination_history', 'has_hospitalization', 'has_medication',
    }
    
    if exposure_form.is_valid():
        new_form_data = detector.extract_new_data(exposure_form)
        form_changes = detector.detect_changes(old_form_data, new_form_data)
        
        # ✅ Filter out fields that are handled by flat field detection
        # Use case-insensitive comparison
        form_changes = [c for c in form_changes 
                       if c['field'] not in flat_field_names 
                       and c['field'].upper() not in flat_field_names
                       and c['field'].lower() not in flat_field_names]
        
        all_changes.extend(form_changes)
        logger.info(f"📝 Form changes (after filter): {len(form_changes)}")
    
    # Flat field changes (vaccines, hospitalizations, medications + radio buttons)
    flat_changes = detect_exp2_flat_field_changes(request, exposure)
    all_changes.extend(flat_changes)
    logger.info(f"📝 Flat changes: {len(flat_changes)}")
    
    # ✅ IMPROVED: Filter out changes where values are actually the same
    def normalize_for_compare(val):
        """Normalize value for comparison - handle None, empty, lowercase"""
        if val is None:
            return ''
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
    logger.info(f"📝 TOTAL changes: {len(all_changes)}")
    
    # ===================================
    # STEP 2: No changes → save directly
    # ===================================
    if not all_changes:
        try:
            with transaction.atomic(using='db_study_44en'):
                # ✅ FIX: Let helper functions handle saving with proper mapping
                # Don't save raw values directly - save_vaccines/hospitalizations/medications will map them
                
                set_audit_metadata(exposure, request.user)
                exposure.save(update_fields=['last_modified_by_id', 'last_modified_by_username'])
                
                save_vaccines(request, exposure)
                save_hospitalizations(request, exposure)
                save_medications(request, exposure)
                
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
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
        
        # Preserve vaccine data from POST
        vaccine_data = {'vaccination_history': request.POST.get('vaccination_history', '')}
        for vaccine_key in ['bcg', 'flu', 'rubella', 'hepa', 'hepb', 'hib', 'chickenpox', 'polio', 
                           'je', 'diphtheria', 'measles', 'meningitis', 'tetanus', 'mumps', 
                           'rabies', 'rotavirus', 'pertussis', 'pneumococcal', 'other']:
            vaccine_data[f'vaccine_{vaccine_key}'] = request.POST.get(f'vaccine_{vaccine_key}') == 'on'
        vaccine_data['vaccine_other_text'] = request.POST.get('vaccine_other_text', '')
        
        # Preserve hospitalization data from POST
        hospitalization_data = {'has_hospitalization': request.POST.get('has_hospitalization', '')}
        for hosp_key in ['central', 'city', 'district', 'private', 'other']:
            hospitalization_data[f'hosp_{hosp_key}'] = request.POST.get(f'hosp_{hosp_key}') == 'on'
            hospitalization_data[f'hosp_{hosp_key}_duration'] = request.POST.get(f'hosp_{hosp_key}_duration', '')
        hospitalization_data['hosp_other_text'] = request.POST.get('hosp_other_text', '')
        
        # Preserve medication data from POST
        medication_data = {'has_medication': request.POST.get('has_medication', '')}
        for med_key in ['antibiotics', 'steroids', 'pain', 'traditional', 'other']:
            medication_data[f'med_{med_key}_exp2'] = request.POST.get(f'med_{med_key}_exp2') == 'on'
            medication_data[f'med_{med_key}_type_exp2'] = request.POST.get(f'med_{med_key}_type_exp2', '')
            medication_data[f'med_{med_key}_duration'] = request.POST.get(f'med_{med_key}_duration', '')
        
        cancel_url = reverse('study_44en:individual:detail', kwargs={'subjectid': subjectid})
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'is_create': False,
            'is_readonly': False,
            'vaccine_data': vaccine_data,
            'hospitalization_data': hospitalization_data,
            'medication_data': medication_data,
            'detected_changes': all_changes,
            'show_reason_form': True,
            'submitted_reasons': reasons_data,
            'cancel_url': cancel_url,
            'edit_post_data': request.POST,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)
    
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
            # ✅ FIX: Let helper functions handle saving with proper mapping
            # Don't save raw values directly - save_vaccines/hospitalizations/medications will map them
            
            set_audit_metadata(exposure, request.user)
            exposure.save(update_fields=['last_modified_by_id', 'last_modified_by_username'])
            logger.info(f"✅ Saved exposure for {subjectid}")
            
            # Update related data (helper functions will set the status fields with proper mapping)
            save_vaccines(request, exposure)
            save_hospitalizations(request, exposure)
            save_medications(request, exposure)
            
            logger.info("=" * 80)
            logger.info(f"=== ✅ UPDATE SUCCESS WITH AUDIT: {subjectid} ===")
            logger.info("=" * 80)
            
            messages.success(request, f'Cập nhật thành công exposure 2 cho {subjectid}!')
            return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
    except Exception as e:
        logger.error(f"❌ Save failed: {e}", exc_info=True)
        messages.error(request, f'Error: {str(e)}')
    
    # Re-render with errors
    vaccine_data = load_vaccines(exposure)
    hospitalization_data = load_hospitalizations(exposure)
    medication_data = load_medications(exposure)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'is_create': False,
        'is_readonly': False,
        'vaccine_data': vaccine_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


@login_required
def individual_exposure_2_view(request, subjectid):
    """VIEW exposure 2 (vaccination & hospitalization) - READ ONLY"""
    logger.info("=== 👁️ EXPOSURE 2 VIEW (READ-ONLY) ===")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    try:
        exposure = Individual_Exposure.objects.get(MEMBERID=individual)
    except Individual_Exposure.DoesNotExist:
        messages.error(request, f'No exposure data found for {subjectid}')
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    # Create readonly form (EXP 2/3 only)
    exposure_form = Individual_Exposure2Form(instance=exposure)
    make_form_readonly(exposure_form)
    
    # Load existing data
    vaccine_data = load_vaccines(exposure)
    hospitalization_data = load_hospitalizations(exposure)
    medication_data = load_medications(exposure)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'is_create': False,
        'is_readonly': True,
        'vaccine_data': vaccine_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
    }
    
    logger.info("=== 👁️ EXPOSURE 2 VIEW END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


# ==========================================
# EXPOSURE 3/3 - FOOD & TRAVEL
# ==========================================

@login_required
def individual_exposure_3_create(request, subjectid):
    """CREATE exposure 3 (food & travel)
    
    ✅ No audit log for CREATE
    """
    logger.info("=" * 80)
    logger.info("=== 🍽️ EXPOSURE 3 CREATE (FOOD & TRAVEL) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # GET - Show blank form
    if request.method == 'GET':
        food_data = load_food_frequency(individual)
        travel_data = load_travel_history(individual)
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'is_create': True,
            'is_readonly': False,
            'food_data': food_data,
            'travel_data': travel_data,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)
    
    # POST
    logger.info("Processing POST - Creating exposure 3")
    
    try:
        with transaction.atomic(using='db_study_44en'):
            # Save food frequency
            save_food_frequency(request, individual)
            
            # Save travel history
            save_travel_history(request, individual)
            
            logger.info("=" * 80)
            logger.info("=== ✅ EXPOSURE 3 CREATE SUCCESS ===")
            logger.info("=" * 80)
            
            messages.success(request, f"Created exposure 3 data for {subjectid}")
            return redirect('study_44en:individual:detail', subjectid=subjectid)
            
    except Exception as e:
        logger.error(f"❌ Error creating exposure 3: {e}", exc_info=True)
        messages.error(request, f'Error creating exposure 3: {str(e)}')
    
    # Re-render with errors
    food_data = load_food_frequency(individual)
    travel_data = load_travel_history(individual)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'is_create': True,
        'is_readonly': False,
        'food_data': food_data,
        'travel_data': travel_data,
    }
    
    logger.info("=== 🍽️ EXPOSURE 3 CREATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


@login_required
@audit_log(model_name='Individual_FoodFrequency', get_patient_id_from='subjectid')
def individual_exposure_3_update(request, subjectid):
    """UPDATE exposure 3 (food & travel)
    
    ✅ MANUAL AUDIT handling for flat fields
    """
    logger.info("=" * 80)
    logger.info("=== 🍽️ EXPOSURE 3 UPDATE (FOOD & TRAVEL) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # GET - Show form with existing data
    if request.method == 'GET':
        logger.info("GET request - Loading existing data")
        
        food_data = load_food_frequency(individual)
        travel_data = load_travel_history(individual)
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'is_create': False,
            'is_readonly': False,
            'food_data': food_data,
            'travel_data': travel_data,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)
    
    # ✅ POST - Manual audit handling
    logger.info("🔄 POST - Manual audit handling")
    
    # ===================================
    # STEP 1: Detect ALL changes
    # ===================================
    validator = ReasonValidator()
    
    # Flat field changes (food frequency, travel)
    all_changes = detect_exp3_flat_field_changes(request, individual)
    
    # ✅ IMPROVED: Filter out changes where values are actually the same
    def normalize_for_compare(val):
        """Normalize value for comparison - handle None, empty, lowercase"""
        if val is None:
            return ''
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
    logger.info(f"📝 TOTAL changes: {len(all_changes)}")
    
    # ===================================
    # STEP 2: No changes → save directly
    # ===================================
    if not all_changes:
        try:
            with transaction.atomic(using='db_study_44en'):
                save_food_frequency(request, individual)
                save_travel_history(request, individual)
                
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
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
        
        # Preserve food data from POST
        food_data = {}
        for template_field in ['freq_rice', 'freq_red_meat', 'freq_poultry', 'freq_seafood', 
                               'freq_eggs', 'freq_raw_veg', 'freq_cooked_veg', 'freq_dairy',
                               'freq_fermented', 'freq_beer', 'freq_alcohol']:
            food_data[template_field] = request.POST.get(template_field, '')
        
        # Preserve travel data from POST
        travel_data = {
            'travel_international': request.POST.get('travel_international', ''),
            'travel_domestic': request.POST.get('travel_domestic', ''),
        }
        
        cancel_url = reverse('study_44en:individual:detail', kwargs={'subjectid': subjectid})
        
        context = {
            'individual': individual,
            'subjectid': subjectid,
            'is_create': False,
            'is_readonly': False,
            'food_data': food_data,
            'travel_data': travel_data,
            'detected_changes': all_changes,
            'show_reason_form': True,
            'submitted_reasons': reasons_data,
            'cancel_url': cancel_url,
            'edit_post_data': request.POST,
        }
        return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)
    
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
            # Update food frequency
            save_food_frequency(request, individual)
            
            # Update travel history
            save_travel_history(request, individual)
            
            logger.info("=" * 80)
            logger.info(f"=== ✅ UPDATE SUCCESS WITH AUDIT: {subjectid} ===")
            logger.info("=" * 80)
            
            messages.success(request, f"Cập nhật thành công exposure 3 cho {subjectid}!")
            return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
            
    except Exception as e:
        logger.error(f"❌ Error updating exposure 3: {e}", exc_info=True)
        messages.error(request, f'Error updating exposure 3: {str(e)}')
    
    # Re-render with errors
    food_data = load_food_frequency(individual)
    travel_data = load_travel_history(individual)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'is_create': False,
        'is_readonly': False,
        'food_data': food_data,
        'travel_data': travel_data,
    }
    
    logger.info("=== 🍽️ EXPOSURE 3 UPDATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


@login_required
def individual_exposure_3_view(request, subjectid):
    """VIEW exposure 3 (food & travel) - READ ONLY"""
    logger.info("=== 👁️ EXPOSURE 3 VIEW (READ-ONLY) ===")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Load existing data
    food_data = load_food_frequency(individual)
    travel_data = load_travel_history(individual)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'is_create': False,
        'is_readonly': True,
        'food_data': food_data,
        'travel_data': travel_data,
    }
    
    logger.info("=== 👁️ EXPOSURE 3 VIEW END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


# ==========================================
# LIST VIEW
# ==========================================

@login_required
def individual_exposure_list(request, subjectid):
    """
    List all exposures for an individual with fixed 3 parts
    """
    logger.info("=" * 80)
    logger.info("=== 📋 INDIVIDUAL EXPOSURE LIST ===")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check which exposure parts exist (OneToOneField - single exposure object)
    exposure = Individual_Exposure.objects.filter(MEMBERID=individual).first()
    
    # Create dictionary: part_number → exposure object (if exists)
    exposures_by_part = {}
    if exposure:
        # Always show all 3 parts as "created" if exposure exists
        exposures_by_part[1] = exposure
        exposures_by_part[2] = exposure
        exposures_by_part[3] = exposure
    
    total_exposures = len(exposures_by_part)
    
    logger.info(f"Found exposure parts: {list(exposures_by_part.keys())}")
    logger.info(f"Total exposure parts completed: {total_exposures}")
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposures_by_part': exposures_by_part,
        'total_exposures': total_exposures,
    }
    
    return render(request, 'studies/study_44en/CRF/individual/exposure_list.html', context)


# ==========================================
# DEPRECATED - Backward compatibility
# ==========================================

@login_required
def individual_exposure(request, subjectid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    Keep for backward compatibility with old URLs
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    if Individual_Exposure.objects.filter(MEMBERID=individual).exists():
        logger.info(f"🔄 Redirecting to update for {subjectid}")
        return redirect('study_44en:individual:exposure_update', subjectid=subjectid)
    else:
        logger.info(f"🔄 Redirecting to create for {subjectid}")
        return redirect('study_44en:individual:exposure_create', subjectid=subjectid)


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # EXP 1/3 - Water & Comorbidities
    'individual_exposure_create',
    'individual_exposure_update',
    'individual_exposure_view',
    
    # EXP 2/3 - Vaccination & Hospitalization
    'individual_exposure_2_create',
    'individual_exposure_2_update',
    'individual_exposure_2_view',
    
    # EXP 3/3 - Food & Travel
    'individual_exposure_3_create',
    'individual_exposure_3_update',
    'individual_exposure_3_view',
    
    # List
    'individual_exposure_list',
    
    # Deprecated
    'individual_exposure',
]