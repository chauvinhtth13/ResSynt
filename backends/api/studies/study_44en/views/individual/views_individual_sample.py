# backends/api/studies/study_44en/views/individual/views_individual_sample.py

"""
Individual Sample Views for Study 44EN
Handles sample collection and food frequency data

REFACTORED: Separated CREATE, UPDATE, and VIEW following household pattern
"""

import logging
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from backends.studies.study_44en.models.individual import (
    Individual, Individual_Sample, Individual_FoodFrequency
)
from backends.studies.study_44en.forms.individual import (
    Individual_SampleForm, Individual_FoodFrequencyForm
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
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Check if sample data already exists
    sample_exists = Individual_Sample.objects.filter(MEMBER=individual).exists()
    food_exists = Individual_FoodFrequency.objects.filter(MEMBER=individual).exists()
    
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
        
        sample_form = Individual_SampleForm(
            request.POST,
            prefix='sample'
        )
        food_frequency_form = Individual_FoodFrequencyForm(
            request.POST,
            prefix='food'
        )
        
        if sample_form.is_valid() and food_frequency_form.is_valid():
            try:
                with transaction.atomic():
                    logger.info("📝 Saving sample data...")
                    
                    # Save sample
                    sample = sample_form.save(commit=False)
                    sample.SUBJECTID = individual
                    set_audit_metadata(sample, request.user)
                    sample.save()
                    logger.info(f"✅ Created sample for {subjectid}")
                    
                    # Save food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.SUBJECTID = individual
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"✅ Created food frequency for {subjectid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ SAMPLE CREATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Created sample data for individual {subjectid}'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error creating sample data: {e}", exc_info=True)
                messages.error(request, f'Error creating sample data: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if sample_form.errors:
                logger.error(f"Sample form errors: {sample_form.errors}")
            if food_frequency_form.errors:
                logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show blank form
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Showing blank form...")
        logger.info("=" * 80)
        
        sample_form = Individual_SampleForm(prefix='sample')
        food_frequency_form = Individual_FoodFrequencyForm(prefix='food')
        logger.info("✅ Blank forms initialized")
    
    context = {
        'individual': individual,
        'sample_form': sample_form,
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
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get sample (must exist for update)
    try:
        sample = Individual_Sample.objects.get(MEMBER=individual)
        logger.info(f"✅ Found sample for {subjectid}")
    except Individual_Sample.DoesNotExist:
        logger.warning(f"⚠️ No sample found for {subjectid}")
        sample = None
    
    # Get food frequency (must exist for update)
    try:
        food_frequency = Individual_FoodFrequency.objects.get(MEMBER=individual)
        logger.info(f"✅ Found food frequency for {subjectid}")
    except Individual_FoodFrequency.DoesNotExist:
        logger.warning(f"⚠️ No food frequency found for {subjectid}")
        food_frequency = None
    
    # If neither exists, redirect to create
    if sample is None and food_frequency is None:
        logger.warning(f"⚠️ No sample data found for {subjectid} - redirecting to create")
        messages.error(
            request,
            f'No sample data found for individual {subjectid}. Please create first.'
        )
        return redirect('study_44en:individual:sample_create', subjectid=subjectid)
    
    # POST - Update sample data
    if request.method == 'POST':
        logger.info("=" * 80)
        logger.info("💾 POST REQUEST - Processing update...")
        logger.info("=" * 80)
        
        sample_form = Individual_SampleForm(
            request.POST,
            instance=sample,
            prefix='sample'
        )
        food_frequency_form = Individual_FoodFrequencyForm(
            request.POST,
            instance=food_frequency,
            prefix='food'
        )
        
        if sample_form.is_valid() and food_frequency_form.is_valid():
            try:
                with transaction.atomic():
                    logger.info("📝 Updating sample data...")
                    
                    # Update sample
                    sample = sample_form.save(commit=False)
                    sample.SUBJECTID = individual
                    set_audit_metadata(sample, request.user)
                    sample.save()
                    logger.info(f"✅ Updated sample for {subjectid}")
                    
                    # Update food frequency
                    food_frequency = food_frequency_form.save(commit=False)
                    food_frequency.SUBJECTID = individual
                    set_audit_metadata(food_frequency, request.user)
                    food_frequency.save()
                    logger.info(f"✅ Updated food frequency for {subjectid}")
                    
                    logger.info("=" * 80)
                    logger.info("=== ✅ SAMPLE UPDATE SUCCESS ===")
                    logger.info("=" * 80)
                    
                    messages.success(
                        request,
                        f'✅ Updated sample data for individual {subjectid}'
                    )
                    return redirect('study_44en:individual:detail', subjectid=subjectid)
                    
            except Exception as e:
                logger.error(f"❌ Error updating sample data: {e}", exc_info=True)
                messages.error(request, f'Error updating sample data: {str(e)}')
        else:
            # Log validation errors
            logger.error("❌ Form validation failed")
            if sample_form.errors:
                logger.error(f"Sample form errors: {sample_form.errors}")
            if food_frequency_form.errors:
                logger.error(f"Food frequency errors: {food_frequency_form.errors}")
            
            messages.error(request, '❌ Please check the form for errors')
    
    # GET - Show form with existing data
    else:
        logger.info("=" * 80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("=" * 80)
        
        sample_form = Individual_SampleForm(
            instance=sample,
            prefix='sample'
        )
        food_frequency_form = Individual_FoodFrequencyForm(
            instance=food_frequency,
            prefix='food'
        )
        logger.info("✅ Forms initialized with existing data")
    
    context = {
        'individual': individual,
        'sample': sample,
        'food_frequency': food_frequency,
        'sample_form': sample_form,
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
    
    # Get individual by MEMBER.MEMBERID (which is the SUBJECTID)
    queryset = get_filtered_individuals(request.user)
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Get sample
    try:
        sample = Individual_Sample.objects.get(MEMBER=individual)
    except Individual_Sample.DoesNotExist:
        sample = None
    
    # Get food frequency
    try:
        food_frequency = Individual_FoodFrequency.objects.get(MEMBER=individual)
    except Individual_FoodFrequency.DoesNotExist:
        food_frequency = None
    
    # If neither exists, redirect to detail
    if sample is None and food_frequency is None:
        messages.error(request, f'No sample data found for individual {subjectid}')
        return redirect('study_44en:individual:detail', subjectid=subjectid)
    
    # Create readonly forms
    sample_form = Individual_SampleForm(
        instance=sample,
        prefix='sample'
    )
    food_frequency_form = Individual_FoodFrequencyForm(
        instance=food_frequency,
        prefix='food'
    )
    
    # Make all forms readonly
    make_form_readonly(sample_form)
    make_form_readonly(food_frequency_form)
    
    context = {
        'individual': individual,
        'sample': sample,
        'food_frequency': food_frequency,
        'sample_form': sample_form,
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
    individual = get_object_or_404(queryset.select_related('MEMBER'), MEMBER__MEMBERID=subjectid)
    
    # Check if sample data exists
    sample_exists = Individual_Sample.objects.filter(MEMBER=individual).exists()
    food_exists = Individual_FoodFrequency.objects.filter(MEMBER=individual).exists()
    
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