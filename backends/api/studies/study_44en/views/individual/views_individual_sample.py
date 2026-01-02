# backends/api/studies/study_44en/views/individual/views_individual_sample.py

"""
Individual Sample Views for Study 44EN
Handles sample collection (4 visit times) and food frequency data

REFACTORED: Using helpers pattern for sample collection
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.individual import (
    Individual, Individual_Sample, Individual_FoodFrequency
)
from backends.studies.study_44en.forms.individual import Individual_FoodFrequencyForm
from backends.api.studies.study_44en.views.views_base import get_filtered_individuals
from .helpers_sample import (
    set_audit_metadata,
    make_form_readonly,
    save_samples,
    load_samples,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
def individual_sample_create(request, subjectid):
    """
    CREATE new sample and food frequency data
    """
    logger.info("=" * 80)
    logger.info("=== 🌱 INDIVIDUAL SAMPLE CREATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    
    # Check if sample data already exists
    sample_exists = Individual_Sample.objects.filter(MEMBERID=individual).exists()
    food_exists = Individual_FoodFrequency.objects.filter(MEMBERID=individual).exists()
    
    if sample_exists or food_exists:
        logger.warning(f"⚠️ Sample data already exists for {subjectid} - redirecting to update")
        messages.warning(
            request,
            f'Sample data already exists for individual {subjectid}. Redirecting to update.'
        )
        return redirect('study_44en:individual:sample_update', subjectid=subjectid)
    
    # POST - Create new sample data
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing creation...")
        logger.info("=" * 80)
        
        food_frequency_form = Individual_FoodFrequencyForm(
            request.POST,
            prefix='food'
        )
        
        if food_frequency_form.is_valid():
            try:
                with transaction.atomic():
                    logger.info("📝 Saving sample data...")
                    
                    # Save samples using helper (handles 4 visit times)
                    save_samples(request, individual)
                    
                    # Save food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.MEMBERID = individual
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"✅ Created food frequency for {subjectid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ SAMPLE CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(request, f'✅ Created sample data for individual {subjectid}')
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating sample data: {e}", exc_info=True)
                messages.error(request, f'Error creating sample data: {str(e)}')
        else:
            logger.error("❌ Form validation failed")
            logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        food_frequency_form = Individual_FoodFrequencyForm(prefix='food')
    
    # Load empty sample data
    sample_data = {}
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'sample_data': sample_data,
        'food_frequency_form': food_frequency_form,
        'is_create': True,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 🌱 SAMPLE CREATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
def individual_sample_update(request, subjectid):
    """
    UPDATE existing sample and food frequency data
    """
    logger.info("=" * 80)
    logger.info("=== 📝 INDIVIDUAL SAMPLE UPDATE START ===")
    logger.info("=" * 80)
    logger.info(f"👤 User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    
    # Get food frequency (may or may not exist)
    try:
        food_frequency = Individual_FoodFrequency.objects.get(MEMBERID=individual)
        logger.info(f"✅ Found food frequency for {subjectid}")
    except Individual_FoodFrequency.DoesNotExist:
        logger.warning(f"⚠️ No food frequency found for {subjectid}")
        food_frequency = None
    
    # POST - Update sample data
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
        food_frequency_form = Individual_FoodFrequencyForm(
            request.POST,
            instance=food_frequency,
            prefix='food'
        )
        
        if food_frequency_form.is_valid():
            try:
                with transaction.atomic():
                    logger.info("📝 Updating sample data...")
                    
                    # Update samples using helper (handles 4 visit times)
                    save_samples(request, individual)
                    
                    # Update food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.MEMBERID = individual
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"✅ Updated food frequency for {subjectid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ SAMPLE UPDATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(request, f'✅ Updated sample data for individual {subjectid}')
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating sample data: {e}", exc_info=True)
                messages.error(request, f'Error updating sample data: {str(e)}')
        else:
            logger.error("❌ Form validation failed")
            logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show form with existing data
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        food_frequency_form = Individual_FoodFrequencyForm(
            instance=food_frequency,
            prefix='food'
        )
    
    # Load existing sample data using helper
    sample_data = load_samples(individual)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'sample_data': sample_data,
        'food_frequency': food_frequency,
        'food_frequency_form': food_frequency_form,
        'is_create': False,
        'is_readonly': False,
    }
    
    logger.info("=" * 80)
    logger.info("=== 📝 SAMPLE UPDATE END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
def individual_sample_view(request, subjectid):
    """
    VIEW sample data (read-only)
    """
    logger.info("=" * 80)
    logger.info("=== 👁️ INDIVIDUAL SAMPLE VIEW (READ-ONLY) ===")
    logger.info("=" * 80)
    
    # Get individual by MEMBERID.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    
    # Get food frequency
    try:
        food_frequency = Individual_FoodFrequency.objects.get(MEMBERID=individual)
    except Individual_FoodFrequency.DoesNotExist:
        food_frequency = None
    
    # Load sample data using helper
    sample_data = load_samples(individual)
    
    # If no data exists, redirect to detail
    if not sample_data and food_frequency is None:
        messages.error(request, f'No sample data found for individual {subjectid}')
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    # Create readonly form for food frequency
    food_frequency_form = Individual_FoodFrequencyForm(
        instance=food_frequency,
        prefix='food'
    )
    make_form_readonly(food_frequency_form)
    
    context = {
        'individual': individual,
        'subjectid': subjectid,
        'sample_data': sample_data,
        'food_frequency': food_frequency,
        'food_frequency_form': food_frequency_form,
        'is_create': False,
        'is_readonly': True,
    }
    
    logger.info("=" * 80)
    logger.info("=== 👁️ SAMPLE VIEW END - Rendering template ===")
    logger.info("=" * 80)
    
    return render(request, 'studies/study_44en/CRF/individual/sample_form.html', context)


# ==========================================
# DEPRECATED - Keep for backward compatibility
# ==========================================

@login_required
def individual_sample(request, subjectid):
    """
    DEPRECATED: Legacy view that handles both create and update
    Redirects to appropriate view based on existence
    
    This is kept for backward compatibility with old URLs
    """
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBERID'), MEMBERID__MEMBERID=subjectid)
    
    # Check if sample data exists
    sample_exists = Individual_Sample.objects.filter(MEMBERID=individual).exists()
    food_exists = Individual_FoodFrequency.objects.filter(MEMBERID=individual).exists()
    
    if sample_exists or food_exists:
        # Data exists - redirect to update
        logger.info(f"🔄 Sample data exists for {subjectid} - redirecting to update")
        return redirect('study_44en:individual:sample_update', subjectid=subjectid)
    else:
        # No data - redirect to create
        logger.info(f"🔄 No sample data for {subjectid} - redirecting to create")
        return redirect('study_44en:individual:sample_create', subjectid=subjectid)


__all__ = [
    'individual_sample_create',
    'individual_sample_update',
    'individual_sample_view',
    'individual_sample',  # Deprecated but kept for compatibility
]