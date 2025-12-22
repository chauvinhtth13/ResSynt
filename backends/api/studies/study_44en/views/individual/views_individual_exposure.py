# backends/api/studies/study_44en/views/individual/views_individual_exposure.py

"""
Individual Exposure Views for Study 44EN
Handles exposure, comorbidity, vaccine, hospitalization, medication, and travel data
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


@login_required
def individual_exposure(request, subjectid):
    """
    Manage individual exposure data with all related formsets
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get or create exposure record
    try:
        exposure = Individual_Exposure.objects.get(SUBJECTID=individual)
        is_create = False
    except Individual_Exposure.DoesNotExist:
        exposure = None
        is_create = True
    
    if request.method == 'POST':
        exposure_form = Individual_ExposureForm(request.POST, instance=exposure)
        
        # Initialize all formsets
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
                    # Save exposure
                    exposure = exposure_form.save(commit=False)
                    exposure.SUBJECTID = individual
                    set_audit_metadata(exposure, request.user)
                    exposure.save()
                    
                    logger.info(f"{'Created' if is_create else 'Updated'} exposure for {subjectid}")
                    
                    # Save all formsets
                    formset_data = [
                        (water_source_formset, 'water sources'),
                        (water_treatment_formset, 'water treatments'),
                        (comorbidity_formset, 'comorbidities'),
                        (vaccine_formset, 'vaccines'),
                        (hospitalization_formset, 'hospitalizations'),
                        (medication_formset, 'medications'),
                        (travel_formset, 'travel history')
                    ]
                    
                    for formset, name in formset_data:
                        instances = formset.save(commit=False)
                        for instance in instances:
                            instance.SUBJECTID = exposure
                            set_audit_metadata(instance, request.user)
                            instance.save()
                        
                        # Handle deletions
                        for obj in formset.deleted_objects:
                            obj.delete()
                        
                        logger.info(f"Saved {len(instances)} {name}")
                    
                    messages.success(
                        request,
                        f'Exposure data for {subjectid} saved successfully.'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"Error saving exposure: {e}", exc_info=True)
                messages.error(request, f'Error saving exposure: {str(e)}')
        else:
            # Log validation errors
            if exposure_form.errors:
                logger.warning(f"Exposure form errors: {exposure_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
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
        'is_create': is_create,
    }
    
    return render(request, 'studies/study_44en/individual/exposure.html', context)


__all__ = ['individual_exposure']
