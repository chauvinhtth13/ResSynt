# backends/api/studies/study_44en/views/household/views_household_case.py
"""
✅ REFACTORED: Household Case CRUD Views - Using Separate Helpers

Following Django development rules:
- Backend-first approach
- Helpers separated into case_helpers.py
- Manual audit handling (no audit_log table in study_44en)

Architecture:
- Main form: HH_CASE
- Formset: HH_Member (1-to-many)
"""

import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import models
from backends.studies.study_44en.models.household import HH_CASE, HH_Member

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_CASEForm,
    HH_MemberFormSet,
)

# Import audit utilities
from backends.audit_log.utils.detector import ChangeDetector
from backends.audit_log.utils.validator import ReasonValidator

# ✅ Import helpers from separate file
from .case_helpers import (
    get_household_with_related,
    save_household_and_related,
    check_household_exists,
    get_household_summary,
    make_form_readonly,
    make_formset_readonly,
    log_all_form_errors,
)

# Import permission decorators
from backends.studies.study_44en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
)

logger = logging.getLogger(__name__)


# ==========================================
# LIST VIEW
# ==========================================

@login_required
@require_crf_view('hh_case')
def household_list(request):
    """
    List all households with search and pagination
    """
    logger.info("="*80)
    logger.info("=== 📋 HOUSEHOLD LIST ===")
    logger.info("="*80)
    
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
        logger.info(f"🔍 Search query: '{search_query}' - Found {households.count()} results")
    
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
    
    logger.info(f"📊 Showing page {page_obj.number} of {paginator.num_pages}")
    
    return render(request, 'studies/study_44en/CRF/base/household_list.html', context)


# ==========================================
# DETAIL VIEW
# ==========================================

@login_required
@require_crf_view('hh_case')
def household_detail(request, hhid):
    """
    View household details with all members and exposure data
    """
    logger.info("="*80)
    logger.info(f"=== 👁️ HOUSEHOLD DETAIL: {hhid} ===")
    logger.info("="*80)
    
    # ✅ Use helper to get household and members
    household, members = get_household_with_related(request, hhid)
    
    # Get respondent info
    respondent = None
    if household.RESPONDENT_MEMBER_NUM:
        respondent = members.filter(MEMBER_NUM=household.RESPONDENT_MEMBER_NUM).first()
        if respondent:
            logger.info(f"👤 Respondent: Member #{respondent.MEMBER_NUM} - {respondent.NAME}")
    
    # Get exposure data (if exists)
    try:
        from backends.studies.study_44en.models.household import (
            HH_Exposure, HH_WaterSource, HH_WaterTreatment, HH_Animal
        )
        exposure = HH_Exposure.objects.get(HHID=household)
        water_sources = HH_WaterSource.objects.filter(HHID=exposure)
        water_treatments = HH_WaterTreatment.objects.filter(HHID=exposure)
        animals = HH_Animal.objects.filter(HHID=exposure)
        logger.info(f"🌱 Exposure data found")
    except HH_Exposure.DoesNotExist:
        exposure = None
        water_sources = []
        water_treatments = []
        animals = []
        logger.info(f"⚠️ No exposure data")
    
    # ✅ Use helper to get summary
    summary = get_household_summary(household)
    
    context = {
        'household': household,
        'members': members,
        'respondent': respondent,
        'summary': summary,
        'total_members': members.count(),
        'exposure': exposure,
        'water_sources': water_sources,
        'water_treatments': water_treatments,
        'animals': animals,
    }
    
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/household/household_detail.html', context)


# ==========================================
# CREATE VIEW (NO AUDIT)
# ==========================================

@login_required
@require_crf_add('hh_case')
def household_create(request):
    """
    ✅ Create new household with members
    
    Following rules:
    - Django Forms handle validation (backend)
    - NO audit needed for CREATE
    - Save main form + formset in transaction using helper
    
    Workflow:
    1. GET: Show blank household form + empty member formset
    2. POST: Validate all forms → Save in transaction → Redirect
    """
    logger.info("="*80)
    logger.info("=== 🏠 HOUSEHOLD CREATE START ===")
    logger.info("="*80)
    logger.info(f"User: {request.user.username}, Method: {request.method}")
    
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
        
        # ✅ Validate both forms (Backend validation)
        household_valid = household_form.is_valid()
        formset_valid = member_formset.is_valid()
        
        logger.info(f"   Household form: {'VALID ✅' if household_valid else 'INVALID ❌'}")
        logger.info(f"   Member formset: {'VALID ✅' if formset_valid else 'INVALID ❌'}")
        
        if household_valid and formset_valid:
            logger.info("💾 All forms valid - Calling save helper...")
            
            # ✅ Use helper to save in transaction
            household = save_household_and_related(
                request=request,
                household_form=household_form,
                member_formset=member_formset,
                is_create=True
            )
            
            if household:
                logger.info("="*80)
                logger.info(f"=== ✅ HOUSEHOLD CREATE SUCCESS: {household.HHID} ===")
                logger.info("="*80)
                
                messages.success(
                    request,
                    f'Đã tạo hộ gia đình {household.HHID} thành công.'
                )
                return redirect('study_44en:household:detail', hhid=household.HHID)
            else:
                logger.error("❌ Save helper returned None")
                messages.error(request, 'Lỗi khi lưu dữ liệu. Vui lòng thử lại.')
        else:
            # ✅ Use helper to log errors
            forms_with_errors = log_all_form_errors({
                'Household Form': household_form,
                'Member Formset': member_formset,
            })
            
            if forms_with_errors:
                error_msg = f'❌ Vui lòng kiểm tra lại: {", ".join(forms_with_errors)}'
                messages.error(request, error_msg)
    
    # GET - Show blank form
    else:
        logger.info("📄 GET REQUEST - Showing blank form...")
        
        household_form = HH_CASEForm()
        member_formset = HH_MemberFormSet(
            instance=None,
            prefix='members'
        )
        
        logger.info("   Blank forms initialized")
    
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
# UPDATE VIEW (MANUAL AUDIT)
# ==========================================

# backends/api/studies/study_44en/views/household/views_household_case.py
"""
✅ FIXED: Household Case UPDATE View - Proper Change Detection

Issue: ChangeDetector was detecting 0 changes even when fields changed
Fix: Use correct detector initialization and comparison
"""

import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import models
from backends.studies.study_44en.models.household import HH_CASE, HH_Member

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_CASEForm,
    HH_MemberFormSet,
)

# Import audit utilities
from backends.audit_log.utils.detector import ChangeDetector
from backends.audit_log.utils.validator import ReasonValidator

# ✅ Import helpers from separate file
from .case_helpers import (
    get_household_with_related,
    save_household_and_related,
    check_household_exists,
    get_household_summary,
    make_form_readonly,
    make_formset_readonly,
    log_all_form_errors,
)

# Import permission decorators
from backends.studies.study_44en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
)

logger = logging.getLogger(__name__)


# ==========================================
# UPDATE VIEW (MANUAL AUDIT) - FIXED
# ==========================================

@login_required
@require_crf_change('hh_case')
def household_update(request, hhid):
    """
    ✅ FIXED: Update household WITH PROPER CHANGE DETECTION
    
    Issue: Was detecting 0 changes even when fields changed
    Fix: Use correct ChangeDetector initialization with instance and form
    
    Architecture:
    - 1 main form (HH_CASE)
    - 1 formset (HH_Member - inline to HH_CASE)
    """
    logger.info("="*80)
    logger.info(f"=== 📝 HOUSEHOLD UPDATE START ===")
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    logger.info("="*80)
    
    # ✅ Use helper to get household with members
    household, members = get_household_with_related(request, hhid)
    logger.info(f"   Household found: {household.HHID}, {members.count()} members")
    
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
        
        logger.info(f"   Forms initialized with existing data")
        logger.info(f"   Members in formset: {len(member_formset.queryset)}")
        
        context = {
            'form': household_form,
            'household_form': household_form,
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
    
    # POST - Process update with change detection
    logger.info("="*80)
    logger.info("💾 POST REQUEST - Processing form submission...")
    logger.info("="*80)
    
    # ===================================
    # CRITICAL FIX: Extract old data BEFORE creating form
    # Django modifies the instance when binding form, so we must
    # capture original values first!
    # ===================================
    detector = ChangeDetector()
    old_form_data = detector.extract_old_data(household)
    logger.info(f"📦 Captured old MONTHLY_INCOME from DB: '{old_form_data.get('MONTHLY_INCOME')}'")
    
    household_form = HH_CASEForm(request.POST, instance=household)
    member_formset = HH_MemberFormSet(
        request.POST,
        instance=household,
        prefix='members'
    )
    
    logger.info("📝 Validating forms...")
    
    # Validate both forms
    form_valid = household_form.is_valid()
    formset_valid = member_formset.is_valid()
    
    logger.info(f"   Household form: {'VALID ✅' if form_valid else 'INVALID ❌'}")
    logger.info(f"   Member formset: {'VALID ✅' if formset_valid else 'INVALID ❌'}")
    
    if form_valid and formset_valid:
        logger.info("✅ All forms valid")
        
        # ===================================
        # STEP 1: DETECT ALL CHANGES
        # ===================================
        validator = ReasonValidator()
        
        # Detect household form changes (old_form_data already extracted BEFORE form creation)
        new_form_data = detector.extract_new_data(household_form)
        logger.info(f"📦 Extracted new MONTHLY_INCOME from form: '{new_form_data.get('MONTHLY_INCOME')}'")
        form_changes = detector.detect_changes(old_form_data, new_form_data)
        
        all_changes = []
        all_changes.extend(form_changes)
        
        # ===================================
        # DETECT MEMBER FORMSET CHANGES
        # ===================================
        member_changes = []
        
        # Get existing members from database
        existing_members = {m.MEMBER_NUM: m for m in members}
        
        for form_idx, member_form in enumerate(member_formset):
            # Skip empty forms
            if not member_form.cleaned_data or member_form.cleaned_data.get('DELETE'):
                continue
            
            member_num = member_form.cleaned_data.get('MEMBER_NUM')
            
            # Check if this is an existing member being edited
            if member_num and member_num in existing_members:
                old_member = existing_members[member_num]
                
                # Extract old and new data for this member
                old_member_data = detector.extract_old_data(old_member)
                new_member_data = detector.extract_new_data(member_form)
                
                # Detect changes for this specific member
                member_specific_changes = detector.detect_changes(old_member_data, new_member_data)
                
                # Add member context to each change
                for change in member_specific_changes:
                    change['member_num'] = member_num
                    change['field'] = f"Member_{member_num}_{change['field']}"
                    member_changes.append(change)
            
            # New member detection (MEMBER_NUM not in existing_members)
            elif member_form.cleaned_data.get('RELATIONSHIP') or member_form.cleaned_data.get('YOB'):
                # This is a new member being added
                new_member_num = member_form.cleaned_data.get('MEMBER_NUM', form_idx + 1)
                logger.info(f"📝 New member detected: Member {new_member_num}")
                
                # Create a change entry for new member
                member_changes.append({
                    'field': f'Member_{new_member_num}_NEW',
                    'old_value': '',
                    'new_value': f"New member: {member_form.cleaned_data.get('RELATIONSHIP', 'Unknown')}",
                    'member_num': new_member_num,
                })
        
        logger.info(f"👥 Member changes detected: {len(member_changes)}")
        all_changes.extend(member_changes)
        
        # Loại bỏ các thay đổi mà giá trị cũ và mới đều rỗng hoặc giống nhau
        all_changes = [c for c in all_changes if (str(c.get('old_value', '')).strip() != str(c.get('new_value', '')).strip()) and not (str(c.get('old_value', '')).strip() == '' and str(c.get('new_value', '')).strip() == '')]
        
        logger.info("="*80)
        logger.info(f"🔍 CHANGE DETECTION RESULT:")
        logger.info(f"   Form changes: {len(form_changes)}")
        logger.info(f"   Total changes (after filter): {len(all_changes)}")
        if all_changes:
            for change in all_changes:
                logger.info(f"   - {change['field']}: '{change['old_value']}' → '{change['new_value']}'")
        logger.info("="*80)
        
        # ===================================
        # STEP 2: NO CHANGES → SAVE DIRECTLY
        # ===================================
        if not all_changes:
            logger.info("💾 No changes detected - Saving directly...")
            
            household = save_household_and_related(
                request=request,
                household_form=household_form,
                member_formset=member_formset,
                is_create=False
            )
            
            if household:
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:household:detail', hhid=hhid)
        
        # ===================================
        # STEP 3: HAS CHANGES → COLLECT REASONS
        # ===================================
        reasons_data = {}
        for change in all_changes:
            reason_key = f'reason_{change["field"]}'
            reason = request.POST.get(reason_key, '').strip()
            if reason:
                reasons_data[change['field']] = reason
        
        # ===================================
        # STEP 4: VALIDATE REASONS
        # ===================================
        required_fields = [c['field'] for c in all_changes]
        validation_result = validator.validate_reasons(reasons_data, required_fields)
        
        if not validation_result['valid']:
            # Show reason modal
            messages.warning(request, 'Vui lòng cung cấp lý do cho tất cả các thay đổi')
            
            logger.warning("⚠️ Changes detected but no/invalid reasons - showing modal")
            logger.info(f"📋 Will show modal for {len(all_changes)} changes")
            
            context = {
                'form': household_form,
                'household_form': household_form,
                'household': household,
                'member_formset': member_formset,
                'is_create': False,
                'is_readonly': False,
                'today': date.today(),
                'show_reason_form': True,  # ✅ CRITICAL: Enable modal
                'detected_changes': all_changes,  # ✅ CRITICAL: Pass changes to template
                'submitted_reasons': reasons_data,  # Preserve submitted reasons
                'cancel_url': reverse('study_44en:household:detail', kwargs={'hhid': hhid}),
            }
            
            logger.info("="*80)
            logger.info("=== 📝 RENDERING TEMPLATE WITH REASON MODAL ===")
            logger.info(f"   show_reason_form: True")
            logger.info(f"   detected_changes: {len(all_changes)} changes")
            logger.info("="*80)
            
            return render(request, 'studies/study_44en/CRF/household/household_form.html', context)
        
        # ===================================
        # STEP 5: SAVE WITH AUDIT
        # ===================================
        sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
        
        # Log the changes and reasons
        logger.info("="*80)
        logger.info("📝 AUDIT TRAIL:")
        logger.info(f"   User: {request.user.username}")
        logger.info(f"   Changes: {len(all_changes)}")
        for change in all_changes:
            reason = sanitized_reasons.get(change['field'], 'N/A')
            logger.info(f"      - {change['field']}: {change['old_value']} → {change['new_value']}")
            logger.info(f"        Reason: {reason}")
        logger.info("="*80)
        
        household = save_household_and_related(
            request=request,
            household_form=household_form,
            member_formset=member_formset,
            is_create=False,
            change_reasons=sanitized_reasons,  # ✅ Pass reasons for audit log
            all_changes=all_changes  # ✅ Pass change details for audit log
        )
        
        if household:
            logger.info("="*80)
            logger.info(f"=== ✅ HOUSEHOLD UPDATE SUCCESS: {household.HHID} ===")
            logger.info("="*80)
            
            messages.success(request, f'Cập nhật household {household.HHID} thành công!')
            return redirect('study_44en:household:detail', hhid=household.HHID)
        else:
            logger.error("❌ Save failed")
            messages.error(request, 'Lỗi khi lưu dữ liệu')
    else:
        # Log validation errors
        logger.error("❌ Form validation failed")
        log_all_form_errors({
            'Household Form': household_form,
            'Member Formset': member_formset,
        })
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # Re-render with errors
    context = {
        'form': household_form,
        'household_form': household_form,
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
@require_crf_view('hh_case')
def household_view(request, hhid):
    """
    ✅ View household (read-only mode)
    
    Following rules:
    - Use backend logic to make forms readonly
    - No JavaScript needed
    """
    logger.info("="*80)
    logger.info(f"=== 👁️ HOUSEHOLD VIEW (READ-ONLY): {hhid} ===")
    logger.info("="*80)
    
    # ✅ Use helper to get household with members
    household, members = get_household_with_related(request, hhid)
    
    # Create readonly forms
    household_form = HH_CASEForm(instance=household)
    member_formset = HH_MemberFormSet(
        instance=household,
        prefix='members'
    )
    
    # ✅ Use helpers to make forms readonly
    make_form_readonly(household_form)
    make_formset_readonly(member_formset)
    
    logger.info(f"   Forms made readonly")
    
    context = {
        'form': household_form,
        'household_form': household_form,
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


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'household_list',
    'household_detail',
    'household_create',
    'household_update',
    'household_view',
]