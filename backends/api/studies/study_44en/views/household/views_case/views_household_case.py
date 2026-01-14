# backends/api/studies/study_44en/views/household/views_household_case.py

import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import models
from backends.studies.study_44en.models.household import HH_CASE, HH_Member
from backends.studies.study_44en.models.per_data import HH_PERSONAL_DATA

# Import forms
from backends.studies.study_44en.forms.household import (
    HH_CASEForm,
    HH_MemberFormSet,
)
from backends.studies.study_44en.forms.per_data import HH_PersonalDataForm

# Import audit utilities
from backends.audit_logs.utils.detector import ChangeDetector
from backends.audit_logs.utils.validator import ReasonValidator

# Import helpers
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
from backends.audit_logs.utils.permission_decorators import (
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
    """List all households with search and pagination"""
    logger.info("="*80)
    logger.info("=== 📋 HOUSEHOLD LIST ===")
    logger.info("="*80)
    
    households = HH_CASE.objects.all().order_by('-HHID')
    
    # Search by HHID (WARD search removed - now encrypted)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        households = households.filter(HHID__icontains=search_query)
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
    
    return render(request, 'studies/study_44en/CRF/base/household_list.html', context)


# ==========================================
# DETAIL VIEW
# ==========================================

@login_required
@require_crf_view('hh_case')
def household_detail(request, hhid):
    """View household details with all members"""
    logger.info("="*80)
    logger.info(f"=== 👁️ HOUSEHOLD DETAIL: {hhid} ===")
    logger.info("="*80)
    
    household, members = get_household_with_related(request, hhid)
    
    # Get personal data (address)
    try:
        personal_data = HH_PERSONAL_DATA.objects.get(HHID=household)
    except HH_PERSONAL_DATA.DoesNotExist:
        personal_data = None
    
    # Get respondent info
    respondent = None
    if household.RESPONDENT_MEMBER_NUM:
        respondent = members.filter(MEMBER_NUM=household.RESPONDENT_MEMBER_NUM).first()
    
    # Get exposure data
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
    
    summary = get_household_summary(household)
    
    context = {
        'household': household,
        'personal_data': personal_data,
        'members': members,
        'respondent': respondent,
        'summary': summary,
        'total_members': members.count(),
        'exposure': exposure,
        'water_sources': water_sources,
        'water_treatments': water_treatments,
        'animals': animals,
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_detail.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('hh_case')
def household_create(request):
    """Create new household with members and personal data"""
    logger.info("="*80)
    logger.info("=== 🏠 HOUSEHOLD CREATE START ===")
    logger.info(f"User: {request.user.username}, Method: {request.method}")
    logger.info("="*80)
    
    if request.method == 'POST':
        logger.info("📨 POST REQUEST - Processing form submission...")
        
        # Initialize all forms
        household_form = HH_CASEForm(request.POST)
        personal_data_form = HH_PersonalDataForm(request.POST)
        member_formset = HH_MemberFormSet(request.POST, instance=None, prefix='members')
        
        # Validate all forms
        household_valid = household_form.is_valid()
        personal_valid = personal_data_form.is_valid()
        formset_valid = member_formset.is_valid()
        
        logger.info(f"   Household form: {'VALID ✅' if household_valid else 'INVALID ❌'}")
        logger.info(f"   Personal data form: {'VALID ✅' if personal_valid else 'INVALID ❌'}")
        logger.info(f"   Member formset: {'VALID ✅' if formset_valid else 'INVALID ❌'}")
        
        if household_valid and personal_valid and formset_valid:
            logger.info("💾 All forms valid - Saving...")
            
            household = save_household_and_related(
                request=request,
                household_form=household_form,
                personal_data_form=personal_data_form,
                member_formset=member_formset,
                is_create=True
            )
            
            if household:
                logger.info(f"=== HOUSEHOLD CREATE SUCCESS: {household.HHID} ===")
                messages.success(request, f'Đã tạo hộ gia đình {household.HHID} thành công.')
                return redirect('study_44en:household:detail', hhid=household.HHID)
            else:
                messages.error(request, 'Lỗi khi lưu dữ liệu. Vui lòng thử lại.')
        else:
            forms_with_errors = log_all_form_errors({
                'Household Form': household_form,
                'Personal Data Form': personal_data_form,
                'Member Formset': member_formset,
            })
            if forms_with_errors:
                messages.error(request, f'❌ Vui lòng kiểm tra lại: {", ".join(forms_with_errors)}')
    else:
        logger.info("📄 GET REQUEST - Showing blank form...")
        household_form = HH_CASEForm()
        personal_data_form = HH_PersonalDataForm(initial={'CITY': 'Ho Chi Minh City'})
        member_formset = HH_MemberFormSet(instance=None, prefix='members')
    
    context = {
        'form': household_form,
        'household_form': household_form,
        'personal_data_form': personal_data_form,
        'member_formset': member_formset,
        'is_create': True,
        'is_readonly': False,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
@require_crf_change('hh_case')
def household_update(request, hhid):
    """Update household with change detection"""
    logger.info("="*80)
    logger.info(f"=== 📝 HOUSEHOLD UPDATE START ===")
    logger.info(f"User: {request.user.username}, HHID: {hhid}, Method: {request.method}")
    logger.info("="*80)
    
    household, members = get_household_with_related(request, hhid)
    
    # Get or create personal data
    personal_data, pd_created = HH_PERSONAL_DATA.objects.get_or_create(
        HHID=household,
        defaults={'CITY': 'Ho Chi Minh City'}
    )
    
    if request.method == 'GET':
        logger.info("📄 GET REQUEST - Loading existing data...")
        
        household_form = HH_CASEForm(instance=household)
        personal_data_form = HH_PersonalDataForm(instance=personal_data)
        member_formset = HH_MemberFormSet(instance=household, prefix='members')
        
        context = {
            'form': household_form,
            'household_form': household_form,
            'personal_data_form': personal_data_form,
            'household': household,
            'member_formset': member_formset,
            'is_create': False,
            'is_readonly': False,
            'today': date.today(),
        }
        
        return render(request, 'studies/study_44en/CRF/household/household_form.html', context)
    
    # POST - Process update
    logger.info("💾 POST REQUEST - Processing form submission...")
    
    # Extract old data BEFORE binding forms
    detector = ChangeDetector()
    old_household_data = detector.extract_old_data(household)
    old_personal_data = detector.extract_old_data(personal_data)
    
    # Bind forms with POST data
    household_form = HH_CASEForm(request.POST, instance=household)
    personal_data_form = HH_PersonalDataForm(request.POST, instance=personal_data)
    member_formset = HH_MemberFormSet(request.POST, instance=household, prefix='members')
    
    # Validate all forms
    form_valid = household_form.is_valid()
    personal_valid = personal_data_form.is_valid()
    formset_valid = member_formset.is_valid()
    
    logger.info(f"   Household form: {'VALID ✅' if form_valid else 'INVALID ❌'}")
    logger.info(f"   Personal data form: {'VALID ✅' if personal_valid else 'INVALID ❌'}")
    logger.info(f"   Member formset: {'VALID ✅' if formset_valid else 'INVALID ❌'}")
    
    if form_valid and personal_valid and formset_valid:
        validator = ReasonValidator()
        
        # Detect changes - Household
        new_household_data = detector.extract_new_data(household_form)
        household_changes = detector.detect_changes(old_household_data, new_household_data)
        
        # Detect changes - Personal Data (address)
        new_personal_data = detector.extract_new_data(personal_data_form)
        personal_changes = detector.detect_changes(old_personal_data, new_personal_data)
        
        # Prefix personal data changes for clarity
        for change in personal_changes:
            change['field'] = f"Address_{change['field']}"
        
        # Detect member changes
        member_changes = []
        existing_members = {m.MEMBER_NUM: m for m in members}
        
        for form_idx, member_form in enumerate(member_formset):
            if not member_form.cleaned_data or member_form.cleaned_data.get('DELETE'):
                continue
            
            member_num = member_form.cleaned_data.get('MEMBER_NUM')
            
            if member_num and member_num in existing_members:
                old_member = existing_members[member_num]
                old_member_data = detector.extract_old_data(old_member)
                new_member_data = detector.extract_new_data(member_form)
                member_specific_changes = detector.detect_changes(old_member_data, new_member_data)
                
                for change in member_specific_changes:
                    change['member_num'] = member_num
                    change['field'] = f"Member_{member_num}_{change['field']}"
                    member_changes.append(change)
            
            elif member_form.cleaned_data.get('RELATIONSHIP') or member_form.cleaned_data.get('BIRTH_YEAR'):
                new_member_num = member_form.cleaned_data.get('MEMBER_NUM', form_idx + 1)
                member_changes.append({
                    'field': f'Member_{new_member_num}_NEW',
                    'old_value': '',
                    'new_value': f"New member: {member_form.cleaned_data.get('RELATIONSHIP', 'Unknown')}",
                    'member_num': new_member_num,
                })
        
        # Combine all changes
        all_changes = household_changes + personal_changes + member_changes
        
        # Filter out empty changes
        all_changes = [c for c in all_changes 
                      if (str(c.get('old_value', '')).strip() != str(c.get('new_value', '')).strip()) 
                      and not (str(c.get('old_value', '')).strip() == '' and str(c.get('new_value', '')).strip() == '')]
        
        logger.info(f"🔍 CHANGE DETECTION: {len(all_changes)} changes")
        for change in all_changes:
            logger.info(f"   - {change['field']}: '{change['old_value']}' → '{change['new_value']}'")
        
        # No changes → save directly
        if not all_changes:
            logger.info("💾 No changes detected - Saving directly...")
            
            household = save_household_and_related(
                request=request,
                household_form=household_form,
                personal_data_form=personal_data_form,
                member_formset=member_formset,
                is_create=False
            )
            
            if household:
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:household:detail', hhid=hhid)
        
        # Has changes → collect reasons
        reasons_data = {}
        for change in all_changes:
            reason_key = f'reason_{change["field"]}'
            reason = request.POST.get(reason_key, '').strip()
            if reason:
                reasons_data[change['field']] = reason
        
        # Validate reasons
        required_fields = [c['field'] for c in all_changes]
        validation_result = validator.validate_reasons(reasons_data, required_fields)
        
        if not validation_result['valid']:
            messages.warning(request, 'Vui lòng cung cấp lý do cho tất cả các thay đổi')
            
            context = {
                'form': household_form,
                'household_form': household_form,
                'personal_data_form': personal_data_form,
                'household': household,
                'member_formset': member_formset,
                'is_create': False,
                'is_readonly': False,
                'today': date.today(),
                'show_reason_form': True,
                'detected_changes': all_changes,
                'submitted_reasons': reasons_data,
                'cancel_url': reverse('study_44en:household:detail', kwargs={'hhid': hhid}),
            }
            
            return render(request, 'studies/study_44en/CRF/household/household_form.html', context)
        
        # Save with audit
        sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
        
        household = save_household_and_related(
            request=request,
            household_form=household_form,
            personal_data_form=personal_data_form,
            member_formset=member_formset,
            is_create=False,
            change_reasons=sanitized_reasons,
            all_changes=all_changes
        )
        
        if household:
            messages.success(request, f'Cập nhật household {household.HHID} thành công!')
            return redirect('study_44en:household:detail', hhid=household.HHID)
        else:
            messages.error(request, 'Lỗi khi lưu dữ liệu')
    else:
        log_all_form_errors({
            'Household Form': household_form,
            'Personal Data Form': personal_data_form,
            'Member Formset': member_formset,
        })
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    context = {
        'form': household_form,
        'household_form': household_form,
        'personal_data_form': personal_data_form,
        'household': household,
        'member_formset': member_formset,
        'is_create': False,
        'is_readonly': False,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('hh_case')
def household_view(request, hhid):
    """View household (read-only mode)"""
    logger.info(f"=== 👁️ HOUSEHOLD VIEW (READ-ONLY): {hhid} ===")
    
    household, members = get_household_with_related(request, hhid)
    
    # Get personal data
    try:
        personal_data = HH_PERSONAL_DATA.objects.get(HHID=household)
    except HH_PERSONAL_DATA.DoesNotExist:
        personal_data = HH_PERSONAL_DATA(HHID=household)
    
    # Create readonly forms
    household_form = HH_CASEForm(instance=household)
    personal_data_form = HH_PersonalDataForm(instance=personal_data)
    member_formset = HH_MemberFormSet(instance=household, prefix='members')
    
    # Make forms readonly
    make_form_readonly(household_form)
    make_form_readonly(personal_data_form)
    make_formset_readonly(member_formset)
    
    context = {
        'form': household_form,
        'household_form': household_form,
        'personal_data_form': personal_data_form,
        'household': household,
        'member_formset': member_formset,
        'is_create': False,
        'is_readonly': True,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


__all__ = [
    'household_list',
    'household_detail',
    'household_create',
    'household_update',
    'household_view',
]
