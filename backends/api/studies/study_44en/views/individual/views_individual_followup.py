# backends/api/studies/study_44en/views/individual/views_individual_followup.py

"""
Individual Follow-up Views for Study 44EN
Handles follow-up visits with symptoms and hospitalization data

REFACTORED: Separated UPDATE and VIEW (split from detail)
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


def make_form_readonly(form):
    """Make all form fields readonly"""
    for field in form.fields.values():
        field.disabled = True


# ==========================================
# LIST VIEW
# ==========================================

@login_required
def individual_followup_list(request, subjectid):
    """
    List all follow-ups for an individual
    """
    logger.info("=" * 80)
    logger.info("=== 📋 INDIVIDUAL FOLLOW-UP LIST ===")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get all follow-ups
    followups = Individual_FollowUp.objects.filter(
        SUBJECTID=individual
    ).order_by('-ASSESSMENT_DATE')
    
    logger.info(f"Found {followups.count()} follow-ups for {subjectid}")
    
    context = {
        'individual': individual,
        'followups': followups,
        'total_followups': followups.count(),
    }
    
    return render(request, 'studies/study_44en/CRF/individual/followup_list.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
def individual_followup_create(request, subjectid):
    """
    CREATE new follow-up visit
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL FOLLOW-UP CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # POST - Create new follow-up
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
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
                    logger.info("📝 Saving follow-up data...")
                    
                    # Save follow-up
                    followup = followup_form.save(commit=False)
                    followup.SUBJECTID = individual
                    set_audit_metadata(followup, request.user)
                    followup.save()
                    logger.info(f"✅ Created follow-up {followup.id} for {subjectid}")
                    
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
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ FOLLOW-UP CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Follow-up visit created successfully'
                    )
                    return redirect('study_44en:individual:followup_list', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating follow-up: {e}", exc_info=True)
                messages.error(request, f'Error saving follow-up: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if followup_form.errors:
                logger.error(f"Follow-up form errors: {followup_form.errors}")
            if symptom_formset.errors:
                logger.error(f"Symptom formset errors: {symptom_formset.errors}")
            if hospitalization_formset.errors:
                logger.error(f"Hospitalization formset errors: {hospitalization_formset.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        
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
        logger.info("✅ Blank forms initialized")
    
    context = {
        'individual': individual,
        'followup_form': followup_form,
        'symptom_formset': symptom_formset,
        'hospitalization_formset': hospitalization_formset,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 🌱 FOLLOW-UP CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/followup_form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
def individual_followup_update(request, subjectid, followup_id):
    """
    UPDATE existing follow-up visit
    """
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL FOLLOW-UP UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, FU ID: {followup_id}, Method: {request.method}")
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get follow-up (must exist for update)
    followup = get_object_or_404(
        Individual_FollowUp,
        id=followup_id,
        SUBJECTID=individual
    )
    logger.info(f"✅ Found follow-up {followup_id}")
    
    # POST - Update follow-up
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
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
                    logger.info("📝 Updating follow-up data...")
                    
                    # Update follow-up
                    followup = followup_form.save(commit=False)
                    set_audit_metadata(followup, request.user)
                    followup.save()
                    logger.info(f"✅ Updated follow-up {followup.id}")
                    
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
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ FOLLOW-UP UPDATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Follow-up visit updated successfully'
                    )
                    return redirect('study_44en:individual:followup_list', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating follow-up: {e}", exc_info=True)
                messages.error(request, f'Error updating follow-up: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if followup_form.errors:
                logger.error(f"Follow-up form errors: {followup_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show form with data
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        followup_form = Individual_FollowUpForm(instance=followup)
        symptom_formset = Individual_SymptomFormSet(
            instance=followup,
            prefix='symptoms'
        )
        hospitalization_formset = Individual_FollowUp_HospitalizationFormSet(
            instance=followup,
            prefix='hospitalizations'
        )
        logger.info("✅ Forms initialized with existing data")
    
    context = {
        'individual': individual,
        'followup': followup,
        'followup_form': followup_form,
        'symptom_formset': symptom_formset,
        'hospitalization_formset': hospitalization_formset,
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
def individual_followup_view(request, subjectid, followup_id):
    """
    VIEW follow-up visit (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL FOLLOW-UP VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get follow-up
    followup = get_object_or_404(
        Individual_FollowUp,
        id=followup_id,
        SUBJECTID=individual
    )
    
    # Create readonly forms
    followup_form = Individual_FollowUpForm(instance=followup)
    symptom_formset = Individual_SymptomFormSet(
        instance=followup,
        prefix='symptoms'
    )
    hospitalization_formset = Individual_FollowUp_HospitalizationFormSet(
        instance=followup,
        prefix='hospitalizations'
    )
    
    # Make all forms readonly
    make_form_readonly(followup_form)
    for form in symptom_formset:
        make_form_readonly(form)
    for form in hospitalization_formset:
        make_form_readonly(form)
    
    context = {
        'individual': individual,
        'followup': followup,
        'followup_form': followup_form,
        'symptom_formset': symptom_formset,
        'hospitalization_formset': hospitalization_formset,
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


__all__ = [
    'individual_followup_list',
    'individual_followup_create',
    'individual_followup_update',   # ✅ NEW: Split from detail
    'individual_followup_view',      # ✅ NEW: Split from detail
    'individual_followup_detail',    # Deprecated alias
]