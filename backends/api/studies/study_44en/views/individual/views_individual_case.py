# backends/api/studies/study_44en/views/individual/views_individual_case.py

"""
Individual Case Views for Study 44EN
Handles Individual CRUD operations

REFACTORED: Renamed individual_edit → individual_update for consistency
"""

import logging
from datetime import date
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.individual import Individual
from backends.studies.study_44en.forms.individual import IndividualForm
from backends.api.studies.study_44en.views.views_base import (
    get_filtered_individuals, get_individual_with_related
)

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


# ==========================================
# LIST VIEW
# ==========================================

@login_required
def individual_list(request):
    """
    List all individuals with search, filter, and pagination
    """
    from backends.api.studies.study_44en.views.views_base import individual_list
    return individual_list(request)


# ==========================================
# DETAIL VIEW
# ==========================================

@login_required
def individual_detail(request, subjectid):
    """
    View individual details with all related data
    """
    queryset = get_filtered_individuals(request.user)
    # Find by MEMBERID.MEMBERID (which is the SUBJECTID)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    
    # Get related counts
    exposure_count = 1 if hasattr(individual, 'exposure') and individual.exposure else 0
    followup_count = individual.follow_ups.count() if hasattr(individual, 'follow_ups') else 0
    sample_count = individual.samples.count() if hasattr(individual, 'samples') else 0
    
    context = {
        'individual': individual,
        'exposure_count': exposure_count,
        'followup_count': followup_count,
        'sample_count': sample_count,
    }
    
    return render(request, 'studies/study_44en/CRF/individual/detail.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
def individual_create(request):
    """
    CREATE new individual
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, Method: {request.method}")
    
    if request.method == 'POST':
        logger.info("💾 POST REQUEST - Processing creation...")
        
        individual_form = IndividualForm(request.POST)
        
        if individual_form.is_valid():
            try:
                with transaction.atomic():
                    # Save individual
                    individual = individual_form.save(commit=False)
                    set_audit_metadata(individual, request.user)
                    individual.save()
                    
                    subjectid = individual.MEMBERID.MEMBERID if individual.MEMBERID else 'N/A'
                    logger.info(f"✅ Created individual: {subjectid}")
                    logger.info("=" * 80)
                    logger.info("=== ✅ INDIVIDUAL CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Individual {subjectid} created successfully.'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating individual: {e}", exc_info=True)
                messages.error(request, f'Error saving individual: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if individual_form.errors:
                logger.error(f"Individual form errors: {individual_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    else:
        # GET - Show blank form
        logger.info("📄 GET REQUEST - Showing blank form...")
        initial_data = {'ENR_DATE': date.today()}
        individual_form = IndividualForm(initial=initial_data)
        logger.info("✅ Blank form initialized")
    
    context = {
        'individual_form': individual_form,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
def individual_update(request, subjectid):
    """
    UPDATE existing individual
    """
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    logger.info(f"✅ Found individual: {subjectid}")
    
    if request.method == 'POST':
        logger.info("💾 POST REQUEST - Processing update...")
        
        individual_form = IndividualForm(request.POST, instance=individual)
        
        if individual_form.is_valid():
            try:
                with transaction.atomic():
                    # Update individual
                    individual = individual_form.save(commit=False)
                    set_audit_metadata(individual, request.user)
                    individual.save()
                    
                    subjectid = individual.MEMBERID.MEMBERID if individual.MEMBERID else 'N/A'
                    logger.info(f"✅ Updated individual: {subjectid}")
                    logger.info("=" * 80)
                    logger.info("=== ✅ INDIVIDUAL UPDATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Individual {subjectid} updated successfully.'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating individual: {e}", exc_info=True)
                messages.error(request, f'Error updating individual: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if individual_form.errors:
                logger.error(f"Individual form errors: {individual_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    else:
        # GET - Show form with data
        logger.info("📄 GET REQUEST - Loading existing data...")
        individual_form = IndividualForm(instance=individual)
        logger.info("✅ Form initialized with existing data")
    
    context = {
        'individual_form': individual_form,
        'individual': individual,
        'is_create': False,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
def individual_view(request, subjectid):
    """
    VIEW individual (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    
    # Create readonly form
    individual_form = IndividualForm(instance=individual)
    
    # Make form readonly
    for field in individual_form.fields.values():
        field.disabled = True
    
    context = {
        'individual_form': individual_form,
        'individual': individual,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/form.html', context)


# ==========================================
# DEPRECATED ALIAS
# ==========================================

@login_required
def individual_edit(request, subjectid):
    """
    DEPRECATED: Alias for individual_update
    Kept for backward compatibility
    """
    logger.warning(f"⚠️ Using deprecated 'individual_edit' - redirecting to 'individual_update'")
    return individual_update(request, subjectid)


__all__ = [
    'individual_list',
    'individual_detail',
    'individual_create',
    'individual_update',  # ✅ NEW: Renamed from individual_edit
    'individual_view',    # ✅ NEW: Read-only view
    'individual_edit',    # Deprecated alias
]