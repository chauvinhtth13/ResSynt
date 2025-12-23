# backends/api/studies/study_44en/views/household/views_household_case.py
"""
Household Case CRUD Views - Following study_43en pattern with Universal Audit System

Handles HH_CASE and HH_Member formset
"""

import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

# Import models
from backends.studies.study_44en.models.household import HH_CASE, HH_Member

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_CASEForm,
    HH_MemberFormSet,
)

# Import utilities (copied from study_43en)
# NOTE: Audit system DISABLED for study_44en - no audit_log table exists
# from backends.studies.study_44en.utils.audit.decorators import audit_log
# from backends.studies.study_44en.utils.audit.processors import process_complex_update

# Import helpers
from .helpers import (
    get_household_with_related,
    save_household_and_related,
    log_all_form_errors,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# LIST VIEW
# ==========================================

@login_required
def household_list(request):
    """
    List all households with search and pagination
    """
    # Get all households
    households = HH_CASE.objects.all().order_by('-HHID')
    
    # Search by HHID or WARD
    search_query = request.GET.get('search', '').strip()
    if search_query:
        households = households.filter(
            HHID__icontains=search_query
        ) | households.filter(
            WARD__icontains=search_query
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(households, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'households': page_obj,
        'search_query': search_query,
        'total_households': households.count(),
    }
    
    return render(request, 'studies/study_44en/CRF/base/household_list.html', context)


# ==========================================
# DETAIL VIEW
# ==========================================

@login_required
def household_detail(request, hhid):
    """
    View household details with all members and exposure data
    """
    household, members = get_household_with_related(request, hhid)
    
    # Get respondent info
    respondent = None
    if household.RESPONDENT_MEMBER_NUM:
        respondent = members.filter(MEMBER_NUM=household.RESPONDENT_MEMBER_NUM).first()
    
    # Get exposure data (if exists)
    try:
        from backends.studies.study_44en.models.household import (
            HH_Exposure, HH_WaterSource, HH_WaterTreatment, HH_Animal
        )
        exposure = HH_Exposure.objects.get(HHID=household)
        water_sources = HH_WaterSource.objects.filter(HHID=exposure)
        water_treatments = HH_WaterTreatment.objects.filter(HHID=exposure)
        animals = HH_Animal.objects.filter(HHID=exposure)
    except HH_Exposure.DoesNotExist:
        exposure = None
        water_sources = []
        water_treatments = []
        animals = []
    
    context = {
        'household': household,
        'members': members,
        'respondent': respondent,
        'total_members': members.count(),
        'exposure': exposure,
        'water_sources': water_sources,
        'water_treatments': water_treatments,
        'animals': animals,
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_detail.html', context)


# ==========================================
# CREATE VIEW (NO AUDIT)
# ==========================================

@login_required
# @audit_log(model_name='HOUSEHOLD', get_patient_id_from='hhid')  # DISABLED - no audit_log table
def household_create(request):
    """
    Create new household with members
    
    Workflow:
    1. Show blank household form
    2. Show 10 member formset rows
    3. Save household + members in transaction
    """
    logger.info("="*80)
    logger.info("=== 🏠 HOUSEHOLD CREATE START ===")
    logger.info("="*80)
    logger.info(f"👤 User: {request.user.username}, Method: {request.method}")
    
    # POST - Process creation
    if request.method == 'POST':
        logger.info("📨 POST REQUEST - Processing form submission...")
        
        # Initialize forms with POST data
        household_form = HH_CASEForm(request.POST)
        member_formset = HH_MemberFormSet(
            request.POST,
            instance=None,
            prefix='members'
        )
        
        logger.info("📝 Validating forms...")
        
        # Validate both forms
        household_valid = household_form.is_valid()
        formset_valid = member_formset.is_valid()
        
        logger.info(f"  Household form: {'✅ VALID' if household_valid else '❌ INVALID'}")
        logger.info(f"  Member formset: {'✅ VALID' if formset_valid else '❌ INVALID'}")
        
        if household_valid and formset_valid:
            logger.info("💾 Calling save_household_and_related...")
            
            household = save_household_and_related(
                request=request,
                household_form=household_form,
                member_formset=member_formset,
                is_create=True
            )
            
            if household:
                logger.info(f"✅ SUCCESS: Household created: {household.HHID}")
                messages.success(
                    request,
                    f'✅ Đã tạo hộ gia đình {household.HHID} thành công.'
                )
                return redirect('study_44en:household:detail', hhid=household.HHID)
            else:
                logger.error("❌ FAILED: save_household_and_related returned None")
                messages.error(request, 'Lỗi khi lưu dữ liệu. Vui lòng thử lại.')
        else:
            # Log errors
            forms_with_errors = log_all_form_errors({
                'Household Form': household_form,
                'Member Formset': member_formset,
            })
            
            if forms_with_errors:
                error_msg = f'❌ Vui lòng kiểm tra lại: {", ".join(forms_with_errors)}'
                messages.error(request, error_msg)
                logger.error(f"Forms with errors: {forms_with_errors}")
    
    # GET - Show blank form
    else:
        logger.info("📄 GET REQUEST - Showing blank form...")
        
        household_form = HH_CASEForm()
        member_formset = HH_MemberFormSet(
            instance=None,
            prefix='members'
        )
        
        logger.info("✅ Blank forms initialized")
    
    # Build context
    context = {
        'form': household_form,
        'household_form': household_form,  # Alias for template compatibility
        'member_formset': member_formset,
        'is_create': True,
        'is_readonly': False,
        'today': date.today(),
    }
    
    logger.info("="*80)
    logger.info("=== 🏠 HOUSEHOLD CREATE END - Rendering template ===")
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


# ==========================================
# UPDATE VIEW (NO AUDIT - study_44en has no audit_log table)
# ==========================================

@login_required
# @audit_log(model_name='HOUSEHOLD', get_patient_id_from='hhid')  # DISABLED - no audit_log table
def household_update(request, hhid):
    """
    Update household WITHOUT audit system (44en has no audit_log table)
    
    Architecture:
    - 1 main form (HH_CASE)
    - 1 formset (HH_Member - inline to HH_CASE)
    """
    logger.info("="*80)
    logger.info("=== 📝 HOUSEHOLD UPDATE START ===")
    logger.info("="*80)
    logger.info(f"👤 User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    
    # Get household with members
    logger.info("📥 Step 1: Fetching household with members...")
    household, members = get_household_with_related(request, hhid)
    logger.info(f"✅ Household found: {household.HHID}, {members.count()} members")
    
    # GET - Show current data
    if request.method == 'GET':
        logger.info("="*80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("="*80)
        
        household_form = HH_CASEForm(instance=household)
        member_formset = HH_MemberFormSet(
            instance=household,
            prefix='members'
        )
        
        logger.info(f"✅ Forms initialized with existing data")
        logger.info(f"   Members in formset: {len(member_formset.queryset)}")
        
        context = {
            'form': household_form,
            'household_form': household_form,  # Alias for template compatibility
            'household': household,
            'member_formset': member_formset,
            'is_create': False,
            'is_readonly': False,
            'current_version': household.version if hasattr(household, 'version') else None,
            'today': date.today(),
        }
        
        logger.info("="*80)
        logger.info("=== 📝 HOUSEHOLD UPDATE END (GET) - Rendering template ===")
        logger.info("="*80)
        
        return render(request, 'studies/study_44en/CRF/household/household_form.html', context)
    
    # POST - Simple save (no audit system)
    logger.info("="*80)
    logger.info("💾 POST REQUEST - Processing form submission...")
    logger.info("="*80)
    
    household_form = HH_CASEForm(request.POST, instance=household)
    member_formset = HH_MemberFormSet(
        request.POST,
        instance=household,
        prefix='members'
    )
    
    logger.info("📝 Step 2: Validating forms...")
    
    # Validate both forms
    form_valid = household_form.is_valid()
    formset_valid = member_formset.is_valid()
    
    if form_valid and formset_valid:
        logger.info("✅ All forms valid - saving...")
        
        # Save using helper
        saved_household = save_household_and_related(
            request=request,
            household_form=household_form,
            member_formset=member_formset,
            is_create=False
        )
        
        if saved_household:
            logger.info(f"✅ SUCCESS - Household {saved_household.HHID} updated")
            messages.success(request, f'Household {saved_household.HHID} updated successfully')
            
            logger.info("="*80)
            logger.info("=== 📝 HOUSEHOLD UPDATE END (POST) - SUCCESS ===")
            logger.info("="*80)
            
            return redirect('study_44en:household:detail', hhid=saved_household.HHID)
        else:
            logger.error("❌ Save failed")
            messages.error(request, 'Failed to save household')
    else:
        logger.error("❌ Form validation failed")
        log_all_form_errors({
            'Household Form': household_form,
            'Member Formset': member_formset,
        })
        messages.error(request, 'Please correct the errors below')
    
    # Re-render with errors
    context = {
        'form': household_form,
        'household_form': household_form,  # Alias for template compatibility
        'household': household,
        'member_formset': member_formset,
        'is_create': False,
        'is_readonly': False,
        'today': date.today(),
        'current_version': household.version if hasattr(household, 'version') else None,
    }
    
    logger.info("="*80)
    logger.info("=== 📝 HOUSEHOLD UPDATE END (POST) - Rendering with errors ===")
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
# @audit_log(model_name='HOUSEHOLD', get_patient_id_from='hhid')  # DISABLED - no audit_log table
def household_view(request, hhid):
    """
    View household (read-only mode)
    """
    logger.info("="*80)
    logger.info("=== 👁️ HOUSEHOLD VIEW (READ-ONLY) ===")
    logger.info("="*80)
    
    # Get household with members
    household, members = get_household_with_related(request, hhid)
    
    # Create readonly forms
    household_form = HH_CASEForm(instance=household)
    member_formset = HH_MemberFormSet(
        instance=household,
        prefix='members'
    )
    
    # Make forms readonly
    make_form_readonly(household_form)
    make_formset_readonly(member_formset)
    
    context = {
        'form': household_form,
        'household_form': household_form,  # Alias for template compatibility
        'household': household,
        'member_formset': member_formset,
        'is_create': False,
        'is_readonly': True,
        'today': date.today(),
    }
    
    logger.info("="*80)
    logger.info("=== 👁️ HOUSEHOLD VIEW END - Rendering template ===")
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)

