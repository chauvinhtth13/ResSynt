# backends/api/studies/study_44en/views/individual/views_individual_followup.py

"""
Individual Follow-up Views for Study 44EN
Handles follow-up visits with symptoms and hospitalization data
"""

import logging
from datetime import date
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.individual import (
    Individual, Individual_FollowUp, Individual_Symptom,
    FollowUp_Hospitalization
)
from backends.studies.study_44en.forms.individual import (
    Individual_FollowUpForm,
    Individual_SymptomFormSet,
    Individual_FollowUp_HospitalizationFormSet
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
def individual_followup_list(request, subjectid):
    """
    List all follow-ups for an individual
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    # Get all follow-ups
    followups = Individual_FollowUp.objects.filter(
        SUBJECTID=individual
    ).order_by('-ASSESSMENT_DATE')
    
    context = {
        'individual': individual,
        'followups': followups,
        'total_followups': followups.count(),
    }
    
    return render(request, 'studies/study_44en/individual/followup_list.html', context)


@login_required
def individual_followup_create(request, subjectid):
    """
    Create new follow-up visit
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    if request.method == 'POST':
        followup_form = Individual_FollowUpForm(request.POST)
        symptom_formset = Individual_SymptomFormSet(
            request.POST, 
            instance=None,
            prefix='symptoms'
        )
        hospitalization_formset = Individual_FollowUp_HospitalizationFormSet(
            request.POST,
            instance=None,
            prefix='hospitalizations'
        )
        
        if all([
            followup_form.is_valid(),
            symptom_formset.is_valid(),
            hospitalization_formset.is_valid()
        ]):
            try:
                with transaction.atomic():
                    # Save follow-up
                    followup = followup_form.save(commit=False)
                    followup.SUBJECTID = individual
                    set_audit_metadata(followup, request.user)
                    followup.save()
                    
                    logger.info(f"Created follow-up {followup.id} for {subjectid}")
                    
                    # Save symptoms
                    symptoms = symptom_formset.save(commit=False)
                    for symptom in symptoms:
                        symptom.SUBJECTID = followup
                        set_audit_metadata(symptom, request.user)
                        symptom.save()
                    
                    logger.info(f"Saved {len(symptoms)} symptoms")
                    
                    # Save hospitalizations
                    hospitalizations = hospitalization_formset.save(commit=False)
                    for hosp in hospitalizations:
                        hosp.FOLLOWUP_ID = followup
                        set_audit_metadata(hosp, request.user)
                        hosp.save()
                    
                    logger.info(f"Saved {len(hospitalizations)} hospitalizations")
                    
                    messages.success(
                        request,
                        f'Follow-up visit created successfully.'
                    )
                    return redirect('study_44en:individual:followup_list', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"Error creating follow-up: {e}", exc_info=True)
                messages.error(request, f'Error saving follow-up: {str(e)}')
        else:
            # Log validation errors
            if followup_form.errors:
                logger.warning(f"Follow-up form errors: {followup_form.errors}")
            if symptom_formset.errors:
                logger.warning(f"Symptom formset errors: {symptom_formset.errors}")
            if hospitalization_formset.errors:
                logger.warning(f"Hospitalization formset errors: {hospitalization_formset.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show blank form
        initial_data = {'ASSESSMENT_DATE': date.today()}
        followup_form = Individual_FollowUpForm(initial=initial_data)
        symptom_formset = Individual_SymptomFormSet(
            instance=None,
            prefix='symptoms'
        )
        hospitalization_formset = Individual_FollowUp_HospitalizationFormSet(
            instance=None,
            prefix='hospitalizations'
        )
    
    context = {
        'individual': individual,
        'followup_form': followup_form,
        'symptom_formset': symptom_formset,
        'hospitalization_formset': hospitalization_formset,
        'is_create': True,
    }
    
    return render(request, 'studies/study_44en/individual/followup_form.html', context)


@login_required
def individual_followup_detail(request, subjectid, followup_id):
    """
    View/edit follow-up visit details
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset, SUBJECTID=subjectid)
    
    followup = get_object_or_404(
        Individual_FollowUp,
        id=followup_id,
        SUBJECTID=individual
    )
    
    if request.method == 'POST':
        followup_form = Individual_FollowUpForm(request.POST, instance=followup)
        symptom_formset = Individual_SymptomFormSet(
            request.POST,
            instance=followup,
            prefix='symptoms'
        )
        hospitalization_formset = Individual_FollowUp_HospitalizationFormSet(
            request.POST,
            instance=followup,
            prefix='hospitalizations'
        )
        
        if all([
            followup_form.is_valid(),
            symptom_formset.is_valid(),
            hospitalization_formset.is_valid()
        ]):
            try:
                with transaction.atomic():
                    # Update follow-up
                    followup = followup_form.save(commit=False)
                    set_audit_metadata(followup, request.user)
                    followup.save()
                    
                    logger.info(f"Updated follow-up {followup.id}")
                    
                    # Save symptoms
                    symptoms = symptom_formset.save(commit=False)
                    for symptom in symptoms:
                        symptom.SUBJECTID = followup
                        set_audit_metadata(symptom, request.user)
                        symptom.save()
                    
                    # Handle deleted symptoms
                    for obj in symptom_formset.deleted_objects:
                        obj.delete()
                    
                    logger.info(f"Saved {len(symptoms)} symptoms")
                    
                    # Save hospitalizations
                    hospitalizations = hospitalization_formset.save(commit=False)
                    for hosp in hospitalizations:
                        hosp.FOLLOWUP_ID = followup
                        set_audit_metadata(hosp, request.user)
                        hosp.save()
                    
                    # Handle deleted hospitalizations
                    for obj in hospitalization_formset.deleted_objects:
                        obj.delete()
                    
                    logger.info(f"Saved {len(hospitalizations)} hospitalizations")
                    
                    messages.success(
                        request,
                        f'Follow-up visit updated successfully.'
                    )
                    return redirect('study_44en:individual:followup_list', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"Error updating follow-up: {e}", exc_info=True)
                messages.error(request, f'Error updating follow-up: {str(e)}')
        else:
            # Log validation errors
            if followup_form.errors:
                logger.warning(f"Follow-up form errors: {followup_form.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
        followup_form = Individual_FollowUpForm(instance=followup)
        symptom_formset = Individual_SymptomFormSet(
            instance=followup,
            prefix='symptoms'
        )
        hospitalization_formset = Individual_FollowUp_HospitalizationFormSet(
            instance=followup,
            prefix='hospitalizations'
        )
    
    context = {
        'individual': individual,
        'followup': followup,
        'followup_form': followup_form,
        'symptom_formset': symptom_formset,
        'hospitalization_formset': hospitalization_formset,
        'is_create': False,
    }
    
    return render(request, 'studies/study_44en/individual/followup_form.html', context)


__all__ = [
    'individual_followup_list',
    'individual_followup_create',
    'individual_followup_detail',
]
