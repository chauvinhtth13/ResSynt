# backends/api/studies/study_44en/views/household/views_household_exposure.py
"""
✅ REFACTORED: Household Exposure Views - Using Universal Audit System

Following Django development rules:
- Backend-first approach
- Universal Audit System (Tier 3 - Complex with formsets)
- Handles multiple formsets: WaterSource, WaterTreatment, Animal
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

# Import models
from backends.studies.study_44en.models.household import (
    HH_CASE,
    HH_Exposure,
    HH_WaterSource,
    HH_WaterTreatment,
    HH_Animal,
)

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_ExposureForm,
    HH_WaterSourceFormSet,
    HH_WaterTreatmentFormSet,
    HH_AnimalFormSet,
)

# ✅ Import Universal Audit System
from backends.audit_log.utils.decorators import audit_log
from backends.audit_log.utils.processors import process_crf_update

# Import permission decorators
from backends.studies.study_44en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
)

# Import helpers
from .helpers import (
    get_household_with_related,
    set_audit_metadata,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS (Backend Logic)
# ==========================================

def save_exposure_and_related(request, forms_dict, household, is_create=False):
    """
    ✅ Backend save logic for exposure + 3 formsets
    
    Args:
        request: HttpRequest
        forms_dict: Dictionary containing validated forms
            - 'main': HH_ExposureForm
            - 'formsets': {
                'water_sources': HH_WaterSourceFormSet,
                'water_treatments': HH_WaterTreatmentFormSet,
                'animals': HH_AnimalFormSet
              }
        household: HH_CASE instance
        is_create: Boolean flag
    
    Returns:
        HH_Exposure instance
    """
    logger.info(f"💾 Saving exposure (is_create={is_create})")
    
    with transaction.atomic(using='db_study_44en'):
        # 1. Save main exposure
        exposure = forms_dict['main'].save(commit=False)
        exposure.HHID = household
        set_audit_metadata(exposure, request.user)
        
        if is_create and hasattr(exposure, 'version'):
            exposure.version = 0
        
        exposure.save()
        logger.info(f"✅ Saved exposure for HHID={household.HHID}")
        
        # 2. Save water sources formset
        if 'formsets' in forms_dict:
            # Water sources
            if 'water_sources' in forms_dict['formsets']:
                ws_formset = forms_dict['formsets']['water_sources']
                water_sources = ws_formset.save(commit=False)
                
                for ws in water_sources:
                    ws.HHID = exposure
                    set_audit_metadata(ws, request.user)
                    ws.save()
                
                for ws in ws_formset.deleted_objects:
                    logger.info(f"🗑️ Deleting water source: {ws.pk}")
                    ws.delete()
                
                logger.info(f"✅ Saved {len(water_sources)} water sources")
            
            # Water treatments
            if 'water_treatments' in forms_dict['formsets']:
                wt_formset = forms_dict['formsets']['water_treatments']
                water_treatments = wt_formset.save(commit=False)
                
                for wt in water_treatments:
                    wt.HHID = exposure
                    set_audit_metadata(wt, request.user)
                    wt.save()
                
                for wt in wt_formset.deleted_objects:
                    logger.info(f"🗑️ Deleting water treatment: {wt.pk}")
                    wt.delete()
                
                logger.info(f"✅ Saved {len(water_treatments)} water treatments")
            
            # Animals
            if 'animals' in forms_dict['formsets']:
                animal_formset = forms_dict['formsets']['animals']
                animals = animal_formset.save(commit=False)
                
                for animal in animals:
                    animal.HHID = exposure
                    set_audit_metadata(animal, request.user)
                    animal.save()
                
                for animal in animal_formset.deleted_objects:
                    logger.info(f"🗑️ Deleting animal: {animal.pk}")
                    animal.delete()
                
                logger.info(f"✅ Saved {len(animals)} animals")
        
        return exposure


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('hh_exposure')
def household_exposure_create(request, hhid):
    """
    ✅ Create new exposure data for household
    
    Following rules:
    - Django Forms handle validation (backend)
    - NO audit needed for CREATE
    """
    logger.info("="*80)
    logger.info("=== 🌊 HOUSEHOLD EXPOSURE CREATE START ===")
    logger.info("="*80)
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Check if exposure already exists
    if HH_Exposure.objects.filter(HHID=household).exists():
        logger.warning(f"⚠️ Exposure already exists for {hhid}")
        messages.warning(
            request,
            f'Exposure data already exists for {hhid}. Redirecting to update.'
        )
        return redirect('study_44en:household:exposure_update', hhid=hhid)
    
    # GET - Show blank forms
    if request.method == 'GET':
        exposure_form = HH_ExposureForm()
        water_source_formset = HH_WaterSourceFormSet(prefix='water_sources')
        water_treatment_formset = HH_WaterTreatmentFormSet(prefix='water_treatments')
        animal_formset = HH_AnimalFormSet(prefix='animals')
        
        context = {
            'household': household,
            'exposure_form': exposure_form,
            'water_source_formset': water_source_formset,
            'water_treatment_formset': water_treatment_formset,
            'animal_formset': animal_formset,
            'is_create': True,
            'is_readonly': False,
        }
        
        logger.info("📄 Showing blank forms")
        return render(
            request,
            'studies/study_44en/CRF/household/household_exposure_form.html',
            context
        )
    
    # POST - Create exposure
    exposure_form = HH_ExposureForm(request.POST)
    water_source_formset = HH_WaterSourceFormSet(
        request.POST,
        prefix='water_sources'
    )
    water_treatment_formset = HH_WaterTreatmentFormSet(
        request.POST,
        prefix='water_treatments'
    )
    animal_formset = HH_AnimalFormSet(
        request.POST,
        prefix='animals'
    )
    
    # ✅ Backend validation (Django Forms)
    all_valid = (
        exposure_form.is_valid() and
        water_source_formset.is_valid() and
        water_treatment_formset.is_valid() and
        animal_formset.is_valid()
    )
    
    if all_valid:
        try:
            # ✅ Use helper to save in transaction
            forms_dict = {
                'main': exposure_form,
                'formsets': {
                    'water_sources': water_source_formset,
                    'water_treatments': water_treatment_formset,
                    'animals': animal_formset,
                }
            }
            
            exposure = save_exposure_and_related(
                request,
                forms_dict,
                household,
                is_create=True
            )
            
            logger.info("="*80)
            logger.info(f"=== ✅ EXPOSURE CREATE SUCCESS: {hhid} ===")
            logger.info("="*80)
            
            messages.success(
                request,
                f'Tạo mới exposure data cho hộ {hhid} thành công!'
            )
            return redirect('study_44en:household:detail', hhid=hhid)
            
        except Exception as e:
            logger.error(f"❌ Create failed: {e}", exc_info=True)
            messages.error(request, f'Lỗi khi tạo: {str(e)}')
    else:
        # Log validation errors
        logger.error("❌ Form validation failed")
        if exposure_form.errors:
            logger.error(f"Exposure errors: {exposure_form.errors}")
        if water_source_formset.errors:
            logger.error(f"Water source errors: {water_source_formset.errors}")
        if water_treatment_formset.errors:
            logger.error(f"Water treatment errors: {water_treatment_formset.errors}")
        if animal_formset.errors:
            logger.error(f"Animal errors: {animal_formset.errors}")
        
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # Re-render with errors
    context = {
        'household': household,
        'exposure_form': exposure_form,
        'water_source_formset': water_source_formset,
        'water_treatment_formset': water_treatment_formset,
        'animal_formset': animal_formset,
        'is_create': True,
        'is_readonly': False,
    }
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_exposure_form.html',
        context
    )


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('hh_exposure')
@audit_log(model_name='HH_EXPOSURE', get_patient_id_from='hhid')
def household_exposure_update(request, hhid):
    """
    ✅ Update exposure WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Following rules:
    - Use Universal Audit System for change tracking
    - Handles 3 formsets automatically
    - Backend handles all logic
    """
    logger.info("="*80)
    logger.info(f"=== 📝 HOUSEHOLD EXPOSURE UPDATE START ===")
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    logger.info("="*80)
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get exposure (must exist for update)
    try:
        exposure = HH_Exposure.objects.select_related('HHID').get(HHID=household)
        logger.info(f"Found exposure for {hhid}")
    except HH_Exposure.DoesNotExist:
        logger.warning(f"⚠️ No exposure found for {hhid}")
        messages.error(
            request,
            f'No exposure data found for {hhid}. Please create first.'
        )
        return redirect('study_44en:household:exposure_create', hhid=hhid)
    
    # GET - Show current data
    if request.method == 'GET':
        exposure_form = HH_ExposureForm(instance=exposure)
        water_source_formset = HH_WaterSourceFormSet(
            instance=exposure,
            prefix='water_sources'
        )
        water_treatment_formset = HH_WaterTreatmentFormSet(
            instance=exposure,
            prefix='water_treatments'
        )
        animal_formset = HH_AnimalFormSet(
            instance=exposure,
            prefix='animals'
        )
        
        context = {
            'household': household,
            'exposure': exposure,
            'exposure_form': exposure_form,
            'water_source_formset': water_source_formset,
            'water_treatment_formset': water_treatment_formset,
            'animal_formset': animal_formset,
            'is_create': False,
            'is_readonly': False,
            'current_version': getattr(exposure, 'version', 0),
        }
        
        logger.info(f"📄 Showing form for HHID={hhid}")
        return render(
            request,
            'studies/study_44en/CRF/household/household_exposure_form.html',
            context
        )
    
    # ✅ POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info("🔄 Using Universal Audit System (Tier 3 - Complex)")
    
    # ✅ Configure forms for Universal Audit
    forms_config = {
        'main': {
            'class': HH_ExposureForm,
            'instance': exposure,
        },
        'formsets': {
            'water_sources': {
                'class': HH_WaterSourceFormSet,
                'instance': exposure,
                'prefix': 'water_sources',
                'related_name': 'hh_watersource_set'
            },
            'water_treatments': {
                'class': HH_WaterTreatmentFormSet,
                'instance': exposure,
                'prefix': 'water_treatments',
                'related_name': 'hh_watertreatment_set'
            },
            'animals': {
                'class': HH_AnimalFormSet,
                'instance': exposure,
                'prefix': 'animals',
                'related_name': 'hh_animal_set'
            }
        }
    }
    
    # ✅ Define save callback
    def save_callback(request, forms_dict):
        return save_exposure_and_related(
            request,
            forms_dict,
            household,
            is_create=False
        )
    
    # ✅ Use Universal Audit System
    return process_crf_update(
        request=request,
        instance=exposure,
        form_class=None,  # Using forms_config instead
        template_name='studies/study_44en/CRF/household/household_exposure_form.html',
        redirect_url=reverse('study_44en:household:detail', kwargs={'hhid': hhid}),
        extra_context={
            'household': household,
            'exposure': exposure,
            'is_create': False,
        },
        forms_config=forms_config,
        save_callback=save_callback,
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('hh_exposure')
def household_exposure_view(request, hhid):
    """
    ✅ View exposure data (read-only)
    
    Following rules:
    - Use template logic to make readonly
    - No JavaScript needed
    """
    logger.info(f"👁️ Read-only view for exposure {hhid}")
    
    # Get household
    household, _ = get_household_with_related(request, hhid)
    
    # Get exposure
    try:
        exposure = HH_Exposure.objects.get(HHID=household)
    except HH_Exposure.DoesNotExist:
        messages.error(request, f'No exposure data found for {hhid}')
        return redirect('study_44en:household:detail', hhid=hhid)
    
    # Create readonly forms
    exposure_form = HH_ExposureForm(instance=exposure)
    water_source_formset = HH_WaterSourceFormSet(
        instance=exposure,
        prefix='water_sources'
    )
    water_treatment_formset = HH_WaterTreatmentFormSet(
        instance=exposure,
        prefix='water_treatments'
    )
    animal_formset = HH_AnimalFormSet(
        instance=exposure,
        prefix='animals'
    )
    
    # ✅ Make all fields readonly (backend logic)
    make_form_readonly(exposure_form)
    make_formset_readonly(water_source_formset)
    make_formset_readonly(water_treatment_formset)
    make_formset_readonly(animal_formset)
    
    context = {
        'household': household,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'water_source_formset': water_source_formset,
        'water_treatment_formset': water_treatment_formset,
        'animal_formset': animal_formset,
        'is_create': False,
        'is_readonly': True,
    }
    
    return render(
        request,
        'studies/study_44en/CRF/household/household_exposure_form.html',
        context
    )


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
@require_crf_view('hh_exposure')
def household_exposure(request, hhid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    
    This is kept for backward compatibility with old URLs
    """
    household, _ = get_household_with_related(request, hhid)
    
    # Check if exposure exists
    if HH_Exposure.objects.filter(HHID=household).exists():
        # Data exists - redirect to update
        logger.info(f"📄 Exposure exists for {hhid} - redirecting to update")
        return redirect('study_44en:household:exposure_update', hhid=hhid)
    else:
        # No data - redirect to create
        logger.info(f"📄 No exposure for {hhid} - redirecting to create")
        return redirect('study_44en:household:exposure_create', hhid=hhid)


__all__ = [
    'household_exposure_create',
    'household_exposure_update',
    'household_exposure_view',
    'household_exposure',  # Deprecated but kept for compatibility
]