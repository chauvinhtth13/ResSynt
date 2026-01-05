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

from backends.studies.study_44en.models.individual import Individual, Individual_FollowUp
from backends.studies.study_44en.forms.individual import Individual_FollowUpForm
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals
from .helpers_followup import (
    set_audit_metadata,
    make_form_readonly,
    save_symptoms,
    save_followup_hospitalizations,
    save_followup_medications,
    load_symptoms,
    load_followup_hospitalizations,
    load_followup_medications,
)

logger = logging.getLogger(__name__)


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
def individual_followup_create(request, subjectid):
    """
    CREATE new follow-up visit
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
            with transaction.atomic():
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
                    assessment_date = request.POST.get('ASSESSMENT_DATE', '').strip()
                    if not assessment_date:
                        raise ValueError('Assessment date is required when participant is assessed')
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
def individual_followup_update(request, subjectid, followup_id):
    """
    UPDATE existing follow-up visit
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
    
    # POST - Update follow-up
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
        try:
            with transaction.atomic():
                logger.info("📝 Updating follow-up data...")
                
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
                    assessment_date = request.POST.get('ASSESSMENT_DATE', '').strip()
                    if not assessment_date:
                        raise ValueError('Assessment date is required when participant is assessed')
                    followup.ASSESSMENT_DATE = assessment_date
                else:
                    # Clear assessment date if not assessed
                    followup.ASSESSMENT_DATE = None
                
                set_audit_metadata(followup, request.user)
                followup.save()
                logger.info(f"Updated follow-up {followup.FUID}")
                
                # Update symptoms using helper
                save_symptoms(request, followup)
                
                # Update hospitalizations using helper
                save_followup_hospitalizations(request, followup)
                
                # Update medications using helper
                save_followup_medications(request, followup)
                
                logger.info("=" * 80)
                logger.info("=== FOLLOW-UP UPDATE SUCCESS ===")
                logger.info("=" * 80)
                
                messages.success(request, f'Follow-up visit updated successfully')
                return redirect('study_44en:individual:followup_list', subjectid=subjectid)
                
        except Exception as e:
            logger.error(f"❌ Error updating follow-up: {e}", exc_info=True)
            messages.error(request, f'Error updating follow-up: {str(e)}')
    
    # GET - Show form with data
    else:
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
    logger.info("=== HHID INDIVIDUAL FOLLOW-UP VIEW (READ-ONLY) ===")
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
    logger.info("=== HHID FOLLOW-UP VIEW END - Rendering template ===")
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
    'individual_followup_update',   # NEW: Split from detail
    'individual_followup_view',      # NEW: Split from detail
    'individual_followup_detail',    # Deprecated alias
]