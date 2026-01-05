"""
Individual Exposure Views for Study 44EN
Handles exposure, comorbidity, vaccine, hospitalization, medication, and travel data

REFACTORED: Clean separation - only CREATE, UPDATE, and VIEW
All business logic moved to helpers_exposure.py
All save/load functions moved to helpers_exposure.py
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.individual import Individual, Individual_Exposure
from backends.studies.study_44en.forms.individual import Individual_ExposureForm, Individual_Exposure2Form
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals
from .helpers_exposure import (
    set_audit_metadata,
    make_form_readonly,
    save_water_sources,
    save_water_treatment,
    save_comorbidities,
    load_water_data,
    load_treatment_data,
    load_comorbidity_data,
    save_vaccines,
    save_hospitalizations,
    save_medications,
    load_vaccines,
    load_hospitalizations,
    load_medications,
    save_food_frequency,
    save_travel_history,
    load_food_frequency,
    load_travel_history,
)

logger = logging.getLogger(__name__)


# ==========================================
# EXPOSURE 1/3 - WATER & COMORBIDITIES
# ==========================================

@login_required
def individual_exposure_create(request, subjectid):
    """CREATE new exposure data (water sources, treatment, comorbidities)"""
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL EXPOSURE CREATE START ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    
    # Get individual
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check if already exists
    if Individual_Exposure.objects.filter(MEMBERID=individual).exists():
        logger.warning(f"Exposure already exists for {subjectid}")
        messages.warning(request, f'Exposure data already exists for {subjectid}. Redirecting to update.')
        return redirect('study_44en:individual:exposure_update', subjectid=subjectid)
    
    if request.method == 'POST':
        logger.info("Processing POST - Creating exposure")
        
        exposure_form = Individual_ExposureForm(request.POST)
        
        if exposure_form.is_valid():
            try:
                with transaction.atomic():
                    # Save main exposure
                    exposure = exposure_form.save(commit=False)
                    exposure.MEMBERID = individual
                    
                    # Handle hardcoded radio buttons not in form
                    shared_toilet = request.POST.get('shared_toilet', '').strip()
                    if shared_toilet:
                        exposure.SHARED_TOILET = shared_toilet
                    
                    # FIX: Save water_treatment Yes/No
                    water_treatment = request.POST.get('water_treatment', '').strip()
                    if water_treatment:
                        exposure.WATER_TREATMENT = water_treatment
                    
                    # FIX: Save has_conditions Yes/No
                    has_conditions = request.POST.get('has_conditions', '').strip()
                    if has_conditions:
                        exposure.HAS_COMORBIDITY = has_conditions
                    
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"Created exposure for {subjectid}")
                    
                    # Save related data using helper functions
                    save_water_sources(request, exposure)
                    save_water_treatment(request, exposure)
                    save_comorbidities(request, exposure)
                    
                    messages.success(request, f'Created exposure data for {subjectid}')
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating exposure: {e}", exc_info=True)
                messages.error(request, f'Error creating exposure: {str(e)}')
        else:
            logger.error(f"Form validation failed: {exposure_form.errors}")
            messages.error(request, '❌ Please check the form for errors')
    
    else:
        # GET - Show blank form
        logger.info("GET request - Showing blank form")
        exposure_form = Individual_ExposureForm()
    
    # Load existing data if any (user might be re-editing after redirect)
    try:
        existing_exposure = Individual_Exposure.objects.get(MEMBERID=individual)
        water_data = load_water_data(existing_exposure)
        treatment_data = load_treatment_data(existing_exposure)
        comorbidity_data = load_comorbidity_data(existing_exposure)
        shared_toilet = existing_exposure.SHARED_TOILET
        logger.info("Loaded existing data for display")
    except Individual_Exposure.DoesNotExist:
        water_data = {}
        treatment_data = {}
        comorbidity_data = {}
        shared_toilet = None
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposure_form': exposure_form,
        'is_create': True,
        'is_readonly': False,
        'water_data': water_data,
        'treatment_data': treatment_data,
        'comorbidity_data': comorbidity_data,
        'shared_toilet': shared_toilet,
    }
    
    logger.info("=== 🌱 EXPOSURE CREATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)


@login_required
def individual_exposure_update(request, subjectid):
    """UPDATE existing exposure data"""
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL EXPOSURE UPDATE START ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    
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
    
    if request.method == 'POST':
        logger.info("Processing POST - Updating exposure")
        
        exposure_form = Individual_ExposureForm(request.POST, instance=exposure)
        
        if exposure_form.is_valid():
            try:
                with transaction.atomic():
                    # Update main exposure
                    exposure = exposure_form.save(commit=False)
                    
                    # Handle hardcoded radio buttons
                    shared_toilet = request.POST.get('shared_toilet', '').strip()
                    if shared_toilet:
                        exposure.SHARED_TOILET = shared_toilet
                    
                    # FIX: Save water_treatment Yes/No
                    water_treatment = request.POST.get('water_treatment', '').strip()
                    if water_treatment:
                        exposure.WATER_TREATMENT = water_treatment
                    
                    # FIX: Save has_conditions Yes/No
                    has_conditions = request.POST.get('has_conditions', '').strip()
                    if has_conditions:
                        exposure.HAS_COMORBIDITY = has_conditions
                    
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"Updated exposure for {subjectid}")
                    
                    # Update related data
                    save_water_sources(request, exposure)
                    save_water_treatment(request, exposure)
                    save_comorbidities(request, exposure)
                    
                    messages.success(request, f'Updated exposure data for {subjectid}')
                    return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating exposure: {e}", exc_info=True)
                messages.error(request, f'Error updating exposure: {str(e)}')
        else:
            logger.error(f"Form validation failed: {exposure_form.errors}")
            messages.error(request, '❌ Please check the form for errors')
    
    else:
        # GET - Show form with existing data
        logger.info("GET request - Loading existing data")
        exposure_form = Individual_ExposureForm(instance=exposure)
    
    # Load existing related data
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
    
    logger.info("=== 📝 EXPOSURE UPDATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)


@login_required
def individual_exposure_view(request, subjectid):
    """VIEW exposure data (read-only)"""
    logger.info("=== HHID INDIVIDUAL EXPOSURE VIEW (READ-ONLY) ===")
    
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
    
    logger.info("=== HHID EXPOSURE VIEW END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_1.html', context)


# ==========================================
# EXPOSURE 2/3 - VACCINATION & HOSPITALIZATION
# ==========================================

@login_required
def individual_exposure_2_create(request, subjectid):
    """CREATE exposure 2 (vaccination & hospitalization)"""
    logger.info("=" * 80)
    logger.info("===  EXPOSURE 2 CREATE (VACCINATION & HOSPITALIZATION) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Check if already exists
    if Individual_Exposure.objects.filter(MEMBERID=individual).exists():
        logger.warning(f"Exposure already exists for {subjectid}")
        messages.warning(request, f'Exposure data already exists for {subjectid}. Redirecting to update.')
        return redirect('study_44en:individual:exposure_2_update', subjectid=subjectid)
    
    if request.method == 'POST':
        logger.info("Processing POST - Creating exposure 2")
        
        # Use separate form for EXP 2/3 only
        exposure_form = Individual_Exposure2Form(request.POST)
        
        if exposure_form.is_valid():
            try:
                with transaction.atomic():
                    # Create new exposure with only EXP 2/3 data
                    exposure = Individual_Exposure(MEMBERID=individual)
                    
                    # Save vaccination_history
                    vaccination_history = request.POST.get('vaccination_history', '').strip()
                    if vaccination_history:
                        exposure.VACCINATION_STATUS = vaccination_history
                    
                    # Save has_hospitalization Yes/No
                    has_hospitalization = request.POST.get('has_hospitalization', '').strip()
                    if has_hospitalization:
                        exposure.HOSPITALIZED_3M = has_hospitalization
                    
                    # Save has_medication Yes/No/Unknown
                    has_medication = request.POST.get('has_medication', '').strip()
                    if has_medication:
                        exposure.MEDICATION_3M = has_medication
                    
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    logger.info(f"Created exposure for {subjectid}")
                    
                    # Save related data
                    save_vaccines(request, exposure)
                    save_hospitalizations(request, exposure)
                    save_medications(request, exposure)
                    
                    messages.success(request, f'Created exposure 2 data for {subjectid}')
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating exposure 2: {e}", exc_info=True)
                messages.error(request, f'Error creating exposure 2: {str(e)}')
        else:
            logger.error(f"Form validation failed: {exposure_form.errors}")
            messages.error(request, '❌ Please check the form for errors')
    
    else:
        exposure_form = Individual_Exposure2Form()
    
    # Load existing data if any
    try:
        existing_exposure = Individual_Exposure.objects.get(MEMBERID=individual)
        vaccine_data = load_vaccines(existing_exposure)
        hospitalization_data = load_hospitalizations(existing_exposure)
        medication_data = load_medications(existing_exposure)
        logger.info("Loaded existing data for display")
    except Individual_Exposure.DoesNotExist:
        vaccine_data = {}
        hospitalization_data = {}
        medication_data = {}
    
    context = {
        'individual': individual,        'subjectid': subjectid,        'exposure_form': exposure_form,
        'is_create': True,
        'is_readonly': False,
        'vaccine_data': vaccine_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
    }
    
    logger.info("===  EXPOSURE 2 CREATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


@login_required
def individual_exposure_2_update(request, subjectid):
    """UPDATE exposure 2 (vaccination & hospitalization)"""
    logger.info("=" * 80)
    logger.info("=== ✏️ EXPOSURE 2 UPDATE (VACCINATION & HOSPITALIZATION) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get exposure
    try:
        exposure = Individual_Exposure.objects.get(MEMBERID=individual)
    except Individual_Exposure.DoesNotExist:
        logger.error(f"No exposure found for {subjectid}")
        messages.error(request, f'No exposure data found for {subjectid}. Please create first.')
        return redirect('study_44en:individual:exposure_2_create', subjectid=subjectid)
    
    if request.method == 'POST':
        logger.info("Processing POST - Updating exposure 2")
        
        # Use separate form for EXP 2/3 only - won't touch EXP 1/3 fields
        exposure_form = Individual_Exposure2Form(request.POST, instance=exposure)
        
        if exposure_form.is_valid():
            try:
                with transaction.atomic():
                    # Only update EXP 2/3 specific fields, preserve EXP 1/3 fields
                    
                    # Save vaccination_history
                    vaccination_history = request.POST.get('vaccination_history', '').strip()
                    if vaccination_history:
                        exposure.VACCINATION_STATUS = vaccination_history
                    
                    # Save has_hospitalization Yes/No
                    has_hospitalization = request.POST.get('has_hospitalization', '').strip()
                    if has_hospitalization:
                        exposure.HOSPITALIZED_3M = has_hospitalization
                    
                    # Save has_medication Yes/No/Unknown
                    has_medication = request.POST.get('has_medication', '').strip()
                    if has_medication:
                        exposure.MEDICATION_3M = has_medication
                    
                    set_audit_metadata(exposure, request.user)
                    exposure.save(update_fields=['VACCINATION_STATUS', 'HOSPITALIZED_3M', 'MEDICATION_3M', 
                                                'last_modified_by_id', 'last_modified_by_username'])
                    logger.info(f"Updated exposure for {subjectid}")
                    
                    # Update related data
                    save_vaccines(request, exposure)
                    save_hospitalizations(request, exposure)
                    save_medications(request, exposure)
                    
                    messages.success(request, f'Updated exposure 2 data for {subjectid}')
                    return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating exposure 2: {e}", exc_info=True)
                messages.error(request, f'Error updating exposure 2: {str(e)}')
        else:
            logger.error(f"Form validation failed: {exposure_form.errors}")
            messages.error(request, '❌ Please check the form for errors')
    
    else:
        logger.info("GET request - Loading existing data")
        exposure_form = Individual_Exposure2Form(instance=exposure)
    
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
        'is_readonly': False,
        'vaccine_data': vaccine_data,
        'hospitalization_data': hospitalization_data,
        'medication_data': medication_data,
    }
    
    logger.info("=== ✏️ EXPOSURE 2 UPDATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


@login_required
def individual_exposure_2_view(request, subjectid):
    """VIEW exposure 2 (vaccination & hospitalization) - READ ONLY"""
    logger.info("=== HHID EXPOSURE 2 VIEW (READ-ONLY) ===")
    
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
    
    logger.info("=== HHID EXPOSURE 2 VIEW END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_2.html', context)


# ==========================================
# EXPOSURE 3/3 - FOOD & TRAVEL
# ==========================================

@login_required
def individual_exposure_3_create(request, subjectid):
    """CREATE exposure 3 (food & travel)"""
    logger.info("=" * 80)
    logger.info("=== 🍽️ EXPOSURE 3 CREATE (FOOD & TRAVEL) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Note: Food frequency and travel are separate from exposure record
    # They link directly to Individual, not Individual_Exposure
    
    if request.method == 'POST':
        logger.info("Processing POST - Creating exposure 3")
        
        try:
            with transaction.atomic():
                # Save food frequency
                save_food_frequency(request, individual)
                
                # Save travel history
                save_travel_history(request, individual)
                
                logger.info("=" * 80)
                logger.info("=== EXPOSURE 3 CREATE SUCCESS ===")
                logger.info("Saved food frequency and travel history")
                logger.info("=" * 80)
                
                messages.success(request, f"Created exposure 3 data for {subjectid}")
                return redirect('study_44en:individual:detail', subjectid=subjectid)
                
        except Exception as e:
            logger.error(f"❌ Error creating exposure 3: {e}", exc_info=True)
            messages.error(request, f'Error creating exposure 3: {str(e)}')
    
    else:
        # GET - Load existing data if any (for re-edit)
        logger.info("GET request - Loading any existing data")
    
    # Load existing data (if any - user might be re-editing)
    food_data = load_food_frequency(individual)
    travel_data = load_travel_history(individual)
    
    context = {
        'individual': individual,
        'is_create': True,
        'is_readonly': False,
        'food_data': food_data,  # CRITICAL: Pass data to template
        'travel_data': travel_data,  # CRITICAL: Pass data to template
    }
    
    logger.info("=== 🍽️ EXPOSURE 3 CREATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


@login_required
def individual_exposure_3_update(request, subjectid):
    """UPDATE exposure 3 (food & travel)"""
    logger.info("=" * 80)
    logger.info("=== 🍽️ EXPOSURE 3 UPDATE (FOOD & TRAVEL) ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    if request.method == 'POST':
        logger.info("Processing POST - Updating exposure 3")
        
        try:
            with transaction.atomic():
                # Update food frequency
                save_food_frequency(request, individual)
                
                # Update travel history
                save_travel_history(request, individual)
                
                logger.info("=" * 80)
                logger.info("=== EXPOSURE 3 UPDATE SUCCESS ===")
                logger.info("Updated food frequency and travel history")
                logger.info("=" * 80)
                
                messages.success(request, f"Updated exposure 3 data for {subjectid}")
                return redirect('study_44en:individual:exposure_list', subjectid=subjectid)
                
        except Exception as e:
            logger.error(f"❌ Error updating exposure 3: {e}", exc_info=True)
            messages.error(request, f'Error updating exposure 3: {str(e)}')
    
    else:
        logger.info("GET request - Loading existing data")
    
    # Load existing data
    food_data = load_food_frequency(individual)
    travel_data = load_travel_history(individual)
    
    context = {
        'individual': individual,        'subjectid': subjectid,        'is_create': False,
        'is_readonly': False,
        'food_data': food_data,
        'travel_data': travel_data,
    }
    
    logger.info("=== 🍽️ EXPOSURE 3 UPDATE END ===")
    return render(request, 'studies/study_44en/CRF/individual/exposure_form_3.html', context)


@login_required
def individual_exposure_3_view(request, subjectid):
    """VIEW exposure 3 (food & travel) - READ ONLY"""
    logger.info("=== HHID EXPOSURE 3 VIEW (READ-ONLY) ===")
    
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
    
    logger.info("=== HHID EXPOSURE 3 VIEW END ===")
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
        # Each part has separate CREATE/UPDATE/VIEW views
        exposures_by_part[1] = exposure
        exposures_by_part[2] = exposure
        exposures_by_part[3] = exposure
    
    total_exposures = len(exposures_by_part)
    
    logger.info(f"Found exposure parts: {list(exposures_by_part.keys())}")
    logger.info(f"Total exposure parts completed: {total_exposures}")
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'exposures_by_part': exposures_by_part,  # Dict for template {% with exposure=exposures_by_part.1 %}
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


__all__ = [
    'individual_exposure_create',
    'individual_exposure_update',
    'individual_exposure_view',
    'individual_exposure',  # Deprecated
    'individual_exposure_2_create',
    'individual_exposure_2_update',
    'individual_exposure_2_view',
    'individual_exposure_3_create',
    'individual_exposure_3_update',
    'individual_exposure_3_view',
]