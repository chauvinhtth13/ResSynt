# backends/api/studies/study_44en/views/household/views_household_exposure.py

"""
Household Exposure Views for Study 44EN
Handles exposure, water sources, treatments, and animals

FINAL FIX: Merge detection into save_callback (no detect_callback parameter)
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.household import (
    HH_CASE, HH_Exposure, HH_WaterSource, HH_WaterTreatment, HH_Animal,
    HH_FoodFrequency, HH_FoodSource
)
from backends.studies.study_44en.models import AuditLog, AuditLogDetail
from backends.studies.study_44en.forms.household import (
    HH_ExposureForm,
    HH_FoodFrequencyForm, HH_FoodSourceForm
)
from ..helpers import (
    get_household_with_related,
    set_audit_metadata,
    make_form_readonly,
)

# Import Universal Audit System
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.detector import ChangeDetector
from backends.audit_logs.utils.validator import ReasonValidator

# Import exposure-specific helpers
from backends.api.studies.study_44en.views.household.views_exposure.exposure_helpers import (
    # Save/Load functions
    save_water_sources,
    save_water_treatment,
    save_animals,
    load_water_data,
    load_treatment_data,
    load_animal_data,
    # Change detection
    detect_flat_field_changes,
)

# Import permission decorators
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW (NO AUDIT)
# ==========================================

@login_required
@require_crf_add('hh_exposure')
def household_exposure_create(request, hhid):
    """CREATE new exposure data for household"""
    logger.info("="*80)
    logger.info("=== 🌱 HOUSEHOLD EXPOSURE CREATE START ===")
    logger.info("="*80)
    
    household, _ = get_household_with_related(request, hhid)
    
    if HH_Exposure.objects.filter(HHID=household).exists():
        messages.warning(request, f'Exposure already exists for {hhid}')
        return redirect('study_44en:household:exposure_update', hhid=hhid)
    
    # GET
    if request.method == 'GET':
        exposure_form = HH_ExposureForm()
        food_freq_form = HH_FoodFrequencyForm()
        food_source_form = HH_FoodSourceForm()
        
        context = {
            'household': household,
            'exposure_form': exposure_form,
            'food_freq_form': food_freq_form,
            'food_source_form': food_source_form,
            'is_create': True,
            'is_readonly': False,
            'water_data': {},
            'treatment_method': None,
            'treatment_other': None,
            'animal_data': {},
        }
        return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)
    
    # POST
    exposure_form = HH_ExposureForm(request.POST)
    food_freq_form = HH_FoodFrequencyForm(request.POST)
    food_source_form = HH_FoodSourceForm(request.POST)
    
    if all([exposure_form.is_valid(), food_freq_form.is_valid(), food_source_form.is_valid()]):
        try:
            with transaction.atomic(using='db_study_44en'):
                exposure = exposure_form.save(commit=False)
                exposure.HHID = household
                set_audit_metadata(exposure, request.user)
                if hasattr(exposure, 'version'):
                    exposure.version = 0
                exposure.save()
                
                save_water_sources(request, exposure)
                save_water_treatment(request, exposure)
                save_animals(request, exposure)
                
                food_freq = food_freq_form.save(commit=False)
                food_freq.HHID = household
                set_audit_metadata(food_freq, request.user)
                food_freq.save()
                
                food_source = food_source_form.save(commit=False)
                food_source.HHID = household
                set_audit_metadata(food_source, request.user)
                food_source.save()
                
                logger.info("=== EXPOSURE CREATE SUCCESS ===")
                messages.success(request, f'Created exposure for {hhid}')
                return redirect('study_44en:household:detail', hhid=hhid)
                
        except Exception as e:
            logger.error(f"❌ Create failed: {e}", exc_info=True)
            messages.error(request, f'Error: {str(e)}')
    else:
        logger.error("❌ Form validation failed")
        messages.error(request, 'Please check form errors')
    
    context = {
        'household': household,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': True,
        'is_readonly': False,
        'water_data': {},
        'treatment_method': None,
        'treatment_other': None,
        'animal_data': {},
    }
    return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)


# ==========================================
# UPDATE VIEW (MANUAL AUDIT)
# ==========================================

@login_required
@require_crf_change('hh_exposure')
@audit_log(
    model_name='HH_EXPOSURE',
    get_patient_id_from='hhid',
    patient_model=HH_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def household_exposure_update(request, hhid):
    """
    UPDATE with MANUAL AUDIT handling
    
    We handle audit manually because flat fields are not in forms
    """
    logger.info("="*80)
    logger.info("=== 📝 HOUSEHOLD EXPOSURE UPDATE START ===")
    logger.info("="*80)
    
    household, _ = get_household_with_related(request, hhid)
    
    try:
        exposure = HH_Exposure.objects.get(HHID=household)
    except HH_Exposure.DoesNotExist:
        messages.error(request, f'No exposure found for {hhid}')
        return redirect('study_44en:household:exposure_create', hhid=hhid)
    
    try:
        food_freq = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_freq = None
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    # GET
    if request.method == 'GET':
        exposure_form = HH_ExposureForm(instance=exposure)
        food_freq_form = HH_FoodFrequencyForm(instance=food_freq)
        food_source_form = HH_FoodSourceForm(instance=food_source)
        
        water_data = load_water_data(exposure)
        treatment_data = load_treatment_data(exposure)
        animal_data = load_animal_data(exposure)
        
        logger.info("="*80)
        logger.info("📋 CONTEXT DEBUG FOR TEMPLATE:")
        logger.info(f"  treatment_method: {treatment_data['method']}")
        logger.info(f"  treatment_other: {treatment_data['other']}")
        logger.info(f"  animal_data: {animal_data}")
        logger.info("="*80)
        
        context = {
            'household': household,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'food_freq_form': food_freq_form,
            'food_source_form': food_source_form,
            'is_create': False,
            'is_readonly': False,
            'water_data': water_data,
            'treatment_method': treatment_data['method'],
            'treatment_other': treatment_data['other'],
            'animal_data': animal_data,
        }
        return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)
    
    # POST - Manual audit handling
    logger.info("POST - Manual audit handling")
    
    # DEBUG: Log POST data
    logger.info("="*80)
    logger.info("📦 POST DATA DEBUG:")
    for key, value in request.POST.items():
        if key.startswith(('TREATMENT', 'animal_', 'WATER_')):
            logger.info(f"  {key}: '{value}'")
    logger.info("="*80)
    
    # STEP 1: Detect ALL changes (form + flat fields)
    detector = ChangeDetector()
    validator = ReasonValidator()
    
    # Form changes
    old_form_data = detector.extract_old_data(exposure)
    exposure_form = HH_ExposureForm(request.POST, instance=exposure)
    
    all_changes = []
    
    if exposure_form.is_valid():
        new_form_data = detector.extract_new_data(exposure_form)
        form_changes = detector.detect_changes(old_form_data, new_form_data)
        all_changes.extend(form_changes)
        logger.info(f"📝 Form changes: {len(form_changes)}")
    
    # Flat field changes
    flat_changes = detect_flat_field_changes(request, exposure)
    all_changes.extend(flat_changes)
    # Loại bỏ các thay đổi mà giá trị cũ và mới đều rỗng hoặc giống nhau
    all_changes = [c for c in all_changes if (str(c.get('old_value', '')).strip() != str(c.get('new_value', '')).strip()) and not (str(c.get('old_value', '')).strip() == '' and str(c.get('new_value', '')).strip() == '')]
    logger.info(f"📝 Flat changes: {len(flat_changes)}")
    logger.info(f"📝 TOTAL changes: {len(all_changes)}")
    
    # STEP 2: No changes → save directly
    if not all_changes:
        try:
            with transaction.atomic(using='db_study_44en'):
                exposure = exposure_form.save(commit=False)
                set_audit_metadata(exposure, request.user)
                exposure.save()
                
                save_water_sources(request, exposure)
                save_water_treatment(request, exposure)
                save_animals(request, exposure)
                
                # Food forms
                food_freq_form = HH_FoodFrequencyForm(request.POST, instance=food_freq)
                if food_freq_form.is_valid():
                    food_freq_obj = food_freq_form.save(commit=False)
                    food_freq_obj.HHID = household
                    set_audit_metadata(food_freq_obj, request.user)
                    food_freq_obj.save()
                
                food_source_form = HH_FoodSourceForm(request.POST, instance=food_source)
                if food_source_form.is_valid():
                    food_source_obj = food_source_form.save(commit=False)
                    food_source_obj.HHID = household
                    set_audit_metadata(food_source_obj, request.user)
                    food_source_obj.save()
                
                messages.success(request, 'Updated successfully!')
                return redirect('study_44en:household:detail', hhid=hhid)
        except Exception as e:
            logger.error(f"❌ Save failed: {e}", exc_info=True)
            messages.error(request, f'Error: {str(e)}')
    
    # STEP 3: Has changes → collect reasons
    reasons_data = {}
    for change in all_changes:
        reason_key = f'reason_{change["field"]}'
        reason = request.POST.get(reason_key, '').strip()
        if reason:
            reasons_data[change['field']] = reason
    
    # STEP 4: Validate reasons
    required_fields = [c['field'] for c in all_changes]
    validation_result = validator.validate_reasons(reasons_data, required_fields)
    
    if not validation_result['valid']:
        # Show reason modal
        messages.warning(request, 'Please provide reasons for all changes')
        
        # PRESERVE NEW POST DATA (not old database values)
        # Extract NEW water source values from POST (preserve user checkbox changes)
        water_data = {}
        source_types = ['tap', 'bottle', 'well', 'rain', 'river', 'pond', 'other']
        for source_key in source_types:
            water_data[f'water_{source_key}_drink'] = request.POST.get(f'water_{source_key}_drink') == 'on'
            water_data[f'water_{source_key}_use'] = request.POST.get(f'water_{source_key}_use') == 'on'
            water_data[f'water_{source_key}_irrigate'] = request.POST.get(f'water_{source_key}_irrigate') == 'on'
            water_data[f'water_{source_key}_other'] = request.POST.get(f'water_{source_key}_other', '')
        
        # Preserve water other source name
        water_data['water_other_src_name'] = request.POST.get('water_other_src_name', '')
        
        # Extract NEW treatment values from POST (preserve user changes)
        new_treatment_method = request.POST.get('TREATMENT_METHOD', '')
        new_treatment_other = request.POST.get('TREATMENT_METHOD_OTHER', '')
        treatment_data = {
            'method': new_treatment_method,
            'other': new_treatment_other
        }
        
        # Extract NEW animal values from POST (preserve user changes)
        animal_data = {}
        for animal in ['dog', 'cat', 'bird', 'poultry', 'cow', 'other']:
            animal_data[animal] = request.POST.get(f'animal_{animal}') == 'on'
        animal_data['other_text'] = request.POST.get('animal_other_text', '')
        
        food_freq_form = HH_FoodFrequencyForm(request.POST, instance=food_freq)
        food_source_form = HH_FoodSourceForm(request.POST, instance=food_source)
        
        from django.urls import reverse
        cancel_url = reverse('study_44en:household:detail', kwargs={'hhid': hhid})
        
        context = {
            'household': household,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'food_freq_form': food_freq_form,
            'food_source_form': food_source_form,
            'is_create': False,
            'is_readonly': False,
            'water_data': water_data,
            'treatment_method': treatment_data['method'],
            'treatment_other': treatment_data['other'],
            'animal_data': animal_data,
            'detected_changes': all_changes,
            'show_reason_form': True,
            'submitted_reasons': reasons_data,
            'cancel_url': cancel_url,
            'edit_post_data': request.POST,  # Pass POST data for template to use
        }
        return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)
    
    # STEP 5: Save with audit
    sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
    
    # Set audit_data for decorator
    combined_reason = "\n".join([
        f"{change['field']}: {sanitized_reasons.get(change['field'], 'N/A')}"
        for change in all_changes
    ])
    
    request.audit_data = {
        'patient_id': hhid,
        'site_id': getattr(household, 'SITEID', None),
        'reason': combined_reason,
        'changes': all_changes,
        'reasons_json': sanitized_reasons,
    }
    
    try:
        with transaction.atomic(using='db_study_44en'):
            # 1. Save main exposure form
            exposure = exposure_form.save(commit=False)
            set_audit_metadata(exposure, request.user)
            exposure.save()
            logger.info(f"Saved exposure for {hhid}")
            
            # 2. Save water sources (flat fields)
            save_water_sources(request, exposure)
            
            # 3. Save water treatment (flat fields)
            save_water_treatment(request, exposure)
            
            # 4. Save animals (flat fields)
            save_animals(request, exposure)
            
            # 5. Validate and save food frequency
            food_freq_form = HH_FoodFrequencyForm(request.POST, instance=food_freq)
            if not food_freq_form.is_valid():
                logger.error(f"Food frequency form invalid: {food_freq_form.errors}")
                raise ValueError(f"Food frequency validation failed: {food_freq_form.errors}")
            
            food_freq_obj = food_freq_form.save(commit=False)
            food_freq_obj.HHID = household
            set_audit_metadata(food_freq_obj, request.user)
            food_freq_obj.save()
            logger.info(f"Saved food frequency for {hhid}")
            
            # 6. Validate and save food source
            food_source_form = HH_FoodSourceForm(request.POST, instance=food_source)
            if not food_source_form.is_valid():
                logger.error(f"Food source form invalid: {food_source_form.errors}")
                raise ValueError(f"Food source validation failed: {food_source_form.errors}")
            
            food_source_obj = food_source_form.save(commit=False)
            food_source_obj.HHID = household
            set_audit_metadata(food_source_obj, request.user)
            food_source_obj.save()
            logger.info(f"Saved food source for {hhid}")
            
            # Audit log will be created automatically by @audit_log decorator
            # because we set request.audit_data above
            
            logger.info("="*80)
            logger.info(f"=== UPDATE SUCCESS WITH AUDIT: {hhid} ===")
            logger.info("="*80)
            
            messages.success(request, f'Cập nhật thành công exposure cho hộ {hhid}!')
            return redirect('study_44en:household:detail', hhid=hhid)
    except Exception as e:
        logger.error(f"❌ Save failed: {e}", exc_info=True)
        messages.error(request, f'Error: {str(e)}')
    
    # Re-render with errors
    water_data = load_water_data(exposure)
    treatment_data = load_treatment_data(exposure)
    animal_data = load_animal_data(exposure)
    
    context = {
        'household': household,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': False,
        'is_readonly': False,
        'water_data': water_data,
        'treatment_method': treatment_data['method'],
        'treatment_other': treatment_data['other'],
        'animal_data': animal_data,
    }
    return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('hh_exposure')
def household_exposure_view(request, hhid):
    """VIEW exposure data (read-only)"""
    household, _ = get_household_with_related(request, hhid)
    
    try:
        exposure = HH_Exposure.objects.get(HHID=household)
    except HH_Exposure.DoesNotExist:
        messages.error(request, f'No exposure found for {hhid}')
        return redirect('study_44en:household:detail', hhid=hhid)
    
    try:
        food_freq = HH_FoodFrequency.objects.get(HHID=household)
    except HH_FoodFrequency.DoesNotExist:
        food_freq = None
    
    try:
        food_source = HH_FoodSource.objects.get(HHID=household)
    except HH_FoodSource.DoesNotExist:
        food_source = None
    
    exposure_form = HH_ExposureForm(instance=exposure)
    food_freq_form = HH_FoodFrequencyForm(instance=food_freq)
    food_source_form = HH_FoodSourceForm(instance=food_source)
    
    make_form_readonly(exposure_form)
    make_form_readonly(food_freq_form)
    make_form_readonly(food_source_form)
    
    water_data = load_water_data(exposure)
    treatment_data = load_treatment_data(exposure)
    animal_data = load_animal_data(exposure)
    
    context = {
        'household': household,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'food_freq_form': food_freq_form,
        'food_source_form': food_source_form,
        'is_create': False,
        'is_readonly': True,
        'water_data': water_data,
        'treatment_method': treatment_data['method'],
        'treatment_other': treatment_data['other'],
        'animal_data': animal_data,
    }
    return render(request, 'studies/study_44en/CRF/household/household_exposure_form.html', context)


# ==========================================
# DEPRECATED
# ==========================================

@login_required
def household_exposure(request, hhid):
    """DEPRECATED: Redirect to appropriate view"""
    household, _ = get_household_with_related(request, hhid)
    
    if HH_Exposure.objects.filter(HHID=household).exists():
        return redirect('study_44en:household:exposure_update', hhid=hhid)
    else:
        return redirect('study_44en:household:exposure_create', hhid=hhid)


__all__ = [
    'household_exposure_create',
    'household_exposure_update',
    'household_exposure_view',
    'household_exposure',
]
