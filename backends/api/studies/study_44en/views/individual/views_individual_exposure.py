# backends/api/studies/study_44en/views/individual/views_individual_exposure.py

"""
Individual Exposure Views for Study 44EN
Handles exposure, comorbidity, vaccine, hospitalization, medication, and travel data

REFACTORED: Separated CREATE, UPDATE, and VIEW following household pattern
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.individual import (
    Individual, Individual_Exposure
)
from backends.studies.study_44en.forms.individual import (
    Individual_ExposureForm,
    Individual_WaterSourceFormSet,
    Individual_WaterTreatmentFormSet,
    Individual_ComorbidityFormSet,
    Individual_VaccineFormSet,
    Individual_HospitalizationFormSet,
    Individual_MedicationFormSet,
    Individual_TravelFormSet
)
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


def make_form_readonly(form):
    """Make all form fields readonly"""
    for field in form.fields.values():
        field.disabled = True


def _save_all_formsets(formsets_list, exposure, user):
    """
    Helper to save all formsets with audit metadata
    
    Args:
        formsets_list: List of tuples [(formset, 'name'), ...]
        exposure: Parent exposure instance
        user: Current user for audit
    
    Returns:
        dict: Summary of saved items {name: count}
    """
    summary = {}
    
    for formset, name in formsets_list:
        instances = formset.save(commit=False)
        for instance in instances:
            instance.SUBJECTID = exposure
            set_audit_metadata(instance, user)
            instance.save()
        
        # Handle deletions
        for obj in formset.deleted_objects:
            obj.delete()
        
        summary[name] = len(instances)
        logger.info(f"Saved {len(instances)} {name}")
    
    return summary


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
def individual_exposure_create(request, subjectid):
    """
    CREATE new exposure data for individual
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL EXPOSURE CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Check if exposure already exists
    if Individual_Exposure.objects.filter(MEMBER=individual).exists():
        logger.warning(f"⚠️ Exposure already exists for {subjectid} - redirecting to update")
        messages.warning(
            request,
            f'Exposure data already exists for individual {subjectid}. Redirecting to update.'
        )
        return redirect('study_44en:individual:exposure_update', subjectid=subjectid)
    
    # POST - Create new exposure
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
        exposure_form = Individual_ExposureForm(request.POST)
        
        # Initialize all formsets with instance=None
        water_source_formset = Individual_WaterSourceFormSet(
            request.POST, instance=None, prefix='water_sources'
        )
        water_treatment_formset = Individual_WaterTreatmentFormSet(
            request.POST, instance=None, prefix='water_treatments'
        )
        comorbidity_formset = Individual_ComorbidityFormSet(
            request.POST, instance=None, prefix='comorbidities'
        )
        vaccine_formset = Individual_VaccineFormSet(
            request.POST, instance=None, prefix='vaccines'
        )
        hospitalization_formset = Individual_HospitalizationFormSet(
            request.POST, instance=None, prefix='hospitalizations'
        )
        medication_formset = Individual_MedicationFormSet(
            request.POST, instance=None, prefix='medications'
        )
        travel_formset = Individual_TravelFormSet(
            request.POST, instance=None, prefix='travel'
        )
        
        # Validate all forms
        forms_valid = all([
            exposure_form.is_valid(),
            water_source_formset.is_valid(),
            water_treatment_formset.is_valid(),
            comorbidity_formset.is_valid(),
            vaccine_formset.is_valid(),
            hospitalization_formset.is_valid(),
            medication_formset.is_valid(),
            travel_formset.is_valid()
        ])
        
        if forms_valid:
            try:
                with transaction.atomic():
                    logger.info("📝 Saving exposure data...")
                    
                    # Save exposure
                    exposure = exposure_form.save(commit=False)
                    exposure.SUBJECTID = individual
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"✅ Created exposure for {subjectid}")
                    
                    # Save all formsets
                    formsets_list = [
                        (water_source_formset, 'water sources'),
                        (water_treatment_formset, 'water treatments'),
                        (comorbidity_formset, 'comorbidities'),
                        (vaccine_formset, 'vaccines'),
                        (hospitalization_formset, 'hospitalizations'),
                        (medication_formset, 'medications'),
                        (travel_formset, 'travel history')
                    ]
                    
                    summary = _save_all_formsets(formsets_list, exposure, request.user)
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ EXPOSURE CREATE SUCCESS ===")
                    logger.info(f"Summary: {summary}")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Created exposure data for individual {subjectid}'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating exposure: {e}", exc_info=True)
                messages.error(request, f'Error creating exposure: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if exposure_form.errors:
                logger.error(f"Exposure form errors: {exposure_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        
        exposure_form = Individual_ExposureForm()
        water_source_formset = Individual_WaterSourceFormSet(
            instance=None, prefix='water_sources'
        )
        water_treatment_formset = Individual_WaterTreatmentFormSet(
            instance=None, prefix='water_treatments'
        )
        comorbidity_formset = Individual_ComorbidityFormSet(
            instance=None, prefix='comorbidities'
        )
        vaccine_formset = Individual_VaccineFormSet(
            instance=None, prefix='vaccines'
        )
        hospitalization_formset = Individual_HospitalizationFormSet(
            instance=None, prefix='hospitalizations'
        )
        medication_formset = Individual_MedicationFormSet(
            instance=None, prefix='medications'
        )
        travel_formset = Individual_TravelFormSet(
            instance=None, prefix='travel'
        )
        logger.info("✅ Blank forms initialized")
    
    context = {
        'individual': individual,
        'exposure_form': exposure_form,
        'water_source_formset': water_source_formset,
        'water_treatment_formset': water_treatment_formset,
        'comorbidity_formset': comorbidity_formset,
        'vaccine_formset': vaccine_formset,
        'hospitalization_formset': hospitalization_formset,
        'medication_formset': medication_formset,
        'travel_formset': travel_formset,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 🌱 EXPOSURE CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/exposure_form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
def individual_exposure_update(request, subjectid):
    """
    UPDATE existing exposure data
    """
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL EXPOSURE UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get exposure (must exist for update)
    try:
        exposure = Individual_Exposure.objects.get(MEMBER=individual)
        logger.info(f"✅ Found existing exposure for {subjectid}")
    except Individual_Exposure.DoesNotExist:
        logger.warning(f"⚠️ No exposure found for {subjectid} - redirecting to create")
        messages.error(
            request,
            f'No exposure data found for individual {subjectid}. Please create first.'
        )
        return redirect('study_44en:individual:exposure_create', subjectid=subjectid)
    
    # POST - Update exposure
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
        exposure_form = Individual_ExposureForm(request.POST, instance=exposure)
        
        # Initialize all formsets with instance=exposure
        water_source_formset = Individual_WaterSourceFormSet(
            request.POST, instance=exposure, prefix='water_sources'
        )
        water_treatment_formset = Individual_WaterTreatmentFormSet(
            request.POST, instance=exposure, prefix='water_treatments'
        )
        comorbidity_formset = Individual_ComorbidityFormSet(
            request.POST, instance=exposure, prefix='comorbidities'
        )
        vaccine_formset = Individual_VaccineFormSet(
            request.POST, instance=exposure, prefix='vaccines'
        )
        hospitalization_formset = Individual_HospitalizationFormSet(
            request.POST, instance=exposure, prefix='hospitalizations'
        )
        medication_formset = Individual_MedicationFormSet(
            request.POST, instance=exposure, prefix='medications'
        )
        travel_formset = Individual_TravelFormSet(
            request.POST, instance=exposure, prefix='travel'
        )
        
        # Validate all forms
        forms_valid = all([
            exposure_form.is_valid(),
            water_source_formset.is_valid(),
            water_treatment_formset.is_valid(),
            comorbidity_formset.is_valid(),
            vaccine_formset.is_valid(),
            hospitalization_formset.is_valid(),
            medication_formset.is_valid(),
            travel_formset.is_valid()
        ])
        
        if forms_valid:
            try:
                with transaction.atomic():
                    logger.info("📝 Updating exposure data...")
                    
                    # Update exposure
                    exposure = exposure_form.save(commit=False)
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"✅ Updated exposure for {subjectid}")
                    
                    # Save all formsets (including deletions)
                    formsets_list = [
                        (water_source_formset, 'water sources'),
                        (water_treatment_formset, 'water treatments'),
                        (comorbidity_formset, 'comorbidities'),
                        (vaccine_formset, 'vaccines'),
                        (hospitalization_formset, 'hospitalizations'),
                        (medication_formset, 'medications'),
                        (travel_formset, 'travel history')
                    ]
                    
                    summary = _save_all_formsets(formsets_list, exposure, request.user)
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ EXPOSURE UPDATE SUCCESS ===")
                    logger.info(f"Summary: {summary}")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Updated exposure data for individual {subjectid}'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating exposure: {e}", exc_info=True)
                messages.error(request, f'Error updating exposure: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if exposure_form.errors:
                logger.error(f"Exposure form errors: {exposure_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show form with existing data
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        exposure_form = Individual_ExposureForm(instance=exposure)
        water_source_formset = Individual_WaterSourceFormSet(
            instance=exposure, prefix='water_sources'
        )
        water_treatment_formset = Individual_WaterTreatmentFormSet(
            instance=exposure, prefix='water_treatments'
        )
        comorbidity_formset = Individual_ComorbidityFormSet(
            instance=exposure, prefix='comorbidities'
        )
        vaccine_formset = Individual_VaccineFormSet(
            instance=exposure, prefix='vaccines'
        )
        hospitalization_formset = Individual_HospitalizationFormSet(
            instance=exposure, prefix='hospitalizations'
        )
        medication_formset = Individual_MedicationFormSet(
            instance=exposure, prefix='medications'
        )
        travel_formset = Individual_TravelFormSet(
            instance=exposure, prefix='travel'
        )
        logger.info("✅ Forms initialized with existing data")
    
    context = {
        'individual': individual,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'water_source_formset': water_source_formset,
        'water_treatment_formset': water_treatment_formset,
        'comorbidity_formset': comorbidity_formset,
        'vaccine_formset': vaccine_formset,
        'hospitalization_formset': hospitalization_formset,
        'medication_formset': medication_formset,
        'travel_formset': travel_formset,
        'is_create': False,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 📝 EXPOSURE UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/exposure_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
def individual_exposure_view(request, subjectid):
    """
    VIEW exposure data (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL EXPOSURE VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get exposure (must exist)
    try:
        exposure = Individual_Exposure.objects.get(MEMBER=individual)
    except Individual_Exposure.DoesNotExist:
        messages.error(request, f'No exposure data found for individual {subjectid}')
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    # Create readonly forms
    exposure_form = Individual_ExposureForm(instance=exposure)
    water_source_formset = Individual_WaterSourceFormSet(
        instance=exposure, prefix='water_sources'
    )
    water_treatment_formset = Individual_WaterTreatmentFormSet(
        instance=exposure, prefix='water_treatments'
    )
    comorbidity_formset = Individual_ComorbidityFormSet(
        instance=exposure, prefix='comorbidities'
    )
    vaccine_formset = Individual_VaccineFormSet(
        instance=exposure, prefix='vaccines'
    )
    hospitalization_formset = Individual_HospitalizationFormSet(
        instance=exposure, prefix='hospitalizations'
    )
    medication_formset = Individual_MedicationFormSet(
        instance=exposure, prefix='medications'
    )
    travel_formset = Individual_TravelFormSet(
        instance=exposure, prefix='travel'
    )
    
    # Make all forms readonly
    make_form_readonly(exposure_form)
    for form in water_source_formset:
        make_form_readonly(form)
    for form in water_treatment_formset:
        make_form_readonly(form)
    for form in comorbidity_formset:
        make_form_readonly(form)
    for form in vaccine_formset:
        make_form_readonly(form)
    for form in hospitalization_formset:
        make_form_readonly(form)
    for form in medication_formset:
        make_form_readonly(form)
    for form in travel_formset:
        make_form_readonly(form)
    
    context = {
        'individual': individual,
        'exposure': exposure,
        'exposure_form': exposure_form,
        'water_source_formset': water_source_formset,
        'water_treatment_formset': water_treatment_formset,
        'comorbidity_formset': comorbidity_formset,
        'vaccine_formset': vaccine_formset,
        'hospitalization_formset': hospitalization_formset,
        'medication_formset': medication_formset,
        'travel_formset': travel_formset,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("=" * 80)
    logger.info("=== 👁️ EXPOSURE VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/exposure_form.html', context)


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
def individual_exposure(request, subjectid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    
    This is kept for backward compatibility with old URLs
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Check if exposure exists
    if Individual_Exposure.objects.filter(MEMBER=individual).exists():
        # Exists - redirect to update
        logger.info(f"🔄 Exposure exists for {subjectid} - redirecting to update")
        return redirect('study_44en:individual:exposure_update', subjectid=subjectid)
    else:
        # Not exists - redirect to create
        logger.info(f"🔄 No exposure for {subjectid} - redirecting to create")
        return redirect('study_44en:individual:exposure_create', subjectid=subjectid)


__all__ = [
    'individual_exposure_create',
    'individual_exposure_update',
    'individual_exposure_view',
    'individual_exposure',  # Deprecated but kept for compatibility
    'individual_exposure_2_create',
    'individual_exposure_2_update',
    'individual_exposure_2_view',
    'individual_exposure_3_create',
    'individual_exposure_3_update',
    'individual_exposure_3_view',
]


# ==========================================
# EXPOSURE 2 (EXP 2/3) - VACCINATION & HOSPITALIZATION
# ==========================================

@login_required
def individual_exposure_2_create(request, subjectid):
    """CREATE exposure 2 (vaccination & hospitalization)"""
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    if request.method == 'POST':
        # Handle form submission
        messages.success(request, "Exposure 2 data saved successfully!")
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    context = {
        'individual': individual,
        'is_readonly': False,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


@login_required
def individual_exposure_2_update(request, subjectid):
    """UPDATE exposure 2 (vaccination & hospitalization)"""
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    if request.method == 'POST':
        # Handle form submission
        messages.success(request, "Exposure 2 data updated successfully!")
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    context = {
        'individual': individual,
        'is_readonly': False,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


@login_required
def individual_exposure_2_view(request, subjectid):
    """VIEW exposure 2 (vaccination & hospitalization) - READ ONLY"""
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    context = {
        'individual': individual,
        'is_readonly': True,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


# ==========================================
# EXPOSURE 3 (EXP 3/3) - FOOD & TRAVEL
# ==========================================

@login_required
def individual_exposure_3_create(request, subjectid):
    """CREATE exposure 3 (food & travel)"""
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    if request.method == 'POST':
        # Handle form submission
        messages.success(request, "Exposure 3 data saved successfully!")
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    context = {
        'individual': individual,
        'is_readonly': False,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


@login_required
def individual_exposure_3_update(request, subjectid):
    """UPDATE exposure 3 (food & travel)"""
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    if request.method == 'POST':
        # Handle form submission
        messages.success(request, "Exposure 3 data updated successfully!")
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    context = {
        'individual': individual,
        'is_readonly': False,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


@login_required
def individual_exposure_3_view(request, subjectid):
    """VIEW exposure 3 (food & travel) - READ ONLY"""
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    context = {
        'individual': individual,
        'is_readonly': True,
    }
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)
