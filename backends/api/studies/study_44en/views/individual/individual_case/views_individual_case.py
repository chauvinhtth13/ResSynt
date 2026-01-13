# backends/api/studies/study_44en/views/individual/views_individual_case.py

"""
REFACTORED: Individual Case Views with Full Audit Support

Following household pattern:
- Manual change detection
- Reason modal workflow
- Audit log creation

Architecture:
- Main form: Individual (single form, no formsets)
"""

import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.individual import Individual
from backends.studies.study_44en.forms.individual import IndividualForm
from backends.studies.study_44en.models import AuditLog, AuditLogDetail

# Import audit utilities
from backends.audit_logs.utils.detector import ChangeDetector
from backends.audit_logs.utils.validator import ReasonValidator
from backends.audit_logs.utils.decorators import audit_log

# Import helpers from separate file
from .case_helpers import (
    get_individual_with_related,
    save_individual,
    check_individual_exists,
    get_individual_summary,
    make_form_readonly,
    log_form_errors,
    set_audit_metadata,
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
@require_crf_view('individual')
def individual_list(request):
    """
    List all individuals with search and pagination
    """
    logger.info("="*80)
    logger.info("=== 📋 INDIVIDUAL LIST ===")
    logger.info("="*80)
    
    # Get all individuals
    individuals = Individual.objects.all().order_by('-SUBJECTID')
    
    # Search by SUBJECTID or MEMBERID
    search_query = request.GET.get('search', '').strip()
    if search_query:
        individuals = individuals.filter(
            SUBJECTID__icontains=search_query
        )
        logger.info(f"🔍 Search query: '{search_query}' - Found {individuals.count()} results")
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(individuals, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'individuals': page_obj,
        'search_query': search_query,
        'total_individuals': individuals.count(),
    }
    
    logger.info(f"📊 Showing page {page_obj.number} of {paginator.num_pages}")
    
    return render(request, 'studies/study_44en/CRF/individual/list.html', context)


# ==========================================
# DETAIL VIEW
# ==========================================

@login_required
@require_crf_view('individual')
def individual_detail(request, subjectid):
    """
    View individual details with all related data
    """
    logger.info("="*80)
    logger.info(f"=== 👁️ INDIVIDUAL DETAIL: {subjectid} ===")
    logger.info("="*80)
    
    # Use helper to get individual
    individual = get_individual_with_related(request, subjectid)
    
    # Use helper to get summary
    summary = get_individual_summary(individual)
    
    context = {
        'individual': individual,
        'summary': summary,
        'exposure_count': summary['exposure_count'],
        'followup_count': summary['followup_count'],
        'sample_count': summary['sample_count'],
    }
    
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/individual/detail.html', context)


# ==========================================
# CREATE VIEW (NO AUDIT)
# ==========================================

@login_required
@require_crf_add('individual')
def individual_create(request):
    """
    Create new individual
    
    Following rules:
    - Django Forms handle validation (backend)
    - NO audit needed for CREATE
    - Save in transaction using helper
    """
    logger.info("="*80)
    logger.info("=== 🌱 INDIVIDUAL CREATE START ===")
    logger.info("="*80)
    logger.info(f"User: {request.user.username}, Method: {request.method}")
    
    # POST - Process creation
    if request.method == 'POST':
        logger.info("📨 POST REQUEST - Processing form submission...")
        
        # Initialize form with POST data
        individual_form = IndividualForm(request.POST)
        
        logger.info("🔍 Validating form...")
        
        # Validate form (Backend validation)
        if individual_form.is_valid():
            logger.info("💾 Form valid - Calling save helper...")
            
            # Use helper to save in transaction
            individual = save_individual(
                request=request,
                individual_form=individual_form,
                is_create=True
            )
            
            if individual:
                subjectid = individual.MEMBERID.MEMBERID if individual.MEMBERID else individual.SUBJECTID
                logger.info("="*80)
                logger.info(f"=== INDIVIDUAL CREATE SUCCESS: {subjectid} ===")
                logger.info("="*80)
                
                messages.success(
                    request,
                    f'Đã tạo individual {subjectid} thành công.'
                )
                return redirect('study_44en:individual:detail', subjectid=subjectid)
            else:
                logger.error("❌ Save helper returned None")
                messages.error(request, 'Lỗi khi lưu dữ liệu. Vui lòng thử lại.')
        else:
            # Use helper to log errors
            log_form_errors(individual_form, 'Individual Form')
            messages.error(request, '❌ Vui lòng kiểm tra lại các trường bị lỗi')
    
    # GET - Show blank form
    else:
        logger.info("📄 GET REQUEST - Showing blank form...")
        
        initial_data = {'ENR_DATE': date.today()}
        individual_form = IndividualForm(initial=initial_data)
        
        logger.info("   Blank form initialized")
    
    # Build context
    context = {
        'individual_form': individual_form,
        'is_create': True,
        'is_readonly': False,
        'today': date.today(),
    }
    
    logger.info("="*80)
    logger.info("=== 🌱 INDIVIDUAL CREATE END - Rendering template ===")
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/individual/form.html', context)


# ==========================================
# UPDATE VIEW (MANUAL AUDIT)
# ==========================================

@login_required
@require_crf_change('individual')
@audit_log(
    model_name='Individual',
    get_patient_id_from='subjectid',
    patient_model=Individual,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def individual_update(request, subjectid):
    """
    UPDATE with MANUAL AUDIT handling
    
    Following household pattern:
    1. Capture old data BEFORE creating form
    2. Detect changes
    3. Collect and validate reasons
    4. Save with audit
    """
    logger.info("="*80)
    logger.info(f"=== 📝 INDIVIDUAL UPDATE START ===")
    logger.info(f"User: {request.user.username}, SUBJECTID: {subjectid}, Method: {request.method}")
    logger.info("="*80)
    
    # Use helper to get individual
    individual = get_individual_with_related(request, subjectid)
    logger.info(f"   Individual found: {individual.SUBJECTID}")
    
    # GET - Show current data
    if request.method == 'GET':
        logger.info("="*80)
        logger.info("📄 GET REQUEST - Loading existing data...")
        logger.info("="*80)
        
        individual_form = IndividualForm(instance=individual)
        
        logger.info(f"   Form initialized with existing data")
        
        context = {
            'individual_form': individual_form,
            'individual': individual,
            'is_create': False,
            'is_readonly': False,
            'current_version': individual.version if hasattr(individual, 'version') else None,
            'today': date.today(),
        }
        
        logger.info("="*80)
        logger.info("=== 📝 INDIVIDUAL UPDATE END (GET) - Rendering template ===")
        logger.info("="*80)
        
        return render(request, 'studies/study_44en/CRF/individual/form.html', context)
    
    # POST - Process update with change detection
    logger.info("="*80)
    logger.info("💾 POST REQUEST - Processing form submission...")
    logger.info("="*80)
    
    # ===================================
    # CRITICAL: Extract old data BEFORE creating form
    # ===================================
    detector = ChangeDetector()
    old_data = detector.extract_old_data(individual)
    logger.info(f"📦 Captured old data from DB")
    
    individual_form = IndividualForm(request.POST, instance=individual)
    
    logger.info("🔍 Validating form...")
    
    # Validate form
    if individual_form.is_valid():
        logger.info("Form valid")
        
        # ===================================
        # STEP 1: DETECT CHANGES
        # ===================================
        validator = ReasonValidator()
        
        # Detect changes
        new_data = detector.extract_new_data(individual_form)
        logger.info(f"📦 Extracted new data from form")
        
        all_changes = detector.detect_changes(old_data, new_data)
        
        # Loại bỏ các thay đổi mà giá trị cũ và mới đều rỗng hoặc giống nhau
        all_changes = [c for c in all_changes if (str(c.get('old_value', '')).strip() != str(c.get('new_value', '')).strip()) and not (str(c.get('old_value', '')).strip() == '' and str(c.get('new_value', '')).strip() == '')]
        
        logger.info("="*80)
        logger.info(f"🔍 CHANGE DETECTION RESULT:")
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
            
            individual = save_individual(
                request=request,
                individual_form=individual_form,
                is_create=False
            )
            
            if individual:
                messages.success(request, 'Lưu thành công!')
                return redirect('study_44en:individual:detail', subjectid=subjectid)
        
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
                'individual_form': individual_form,
                'individual': individual,
                'is_create': False,
                'is_readonly': False,
                'today': date.today(),
                'show_reason_form': True,  # CRITICAL: Enable modal
                'detected_changes': all_changes,  # CRITICAL: Pass changes to template
                'submitted_reasons': reasons_data,  # Preserve submitted reasons
                'cancel_url': reverse('study_44en:individual:detail', kwargs={'subjectid': subjectid}),
                'edit_post_data': dict(request.POST.items()),  # Pass POST data for resubmission
            }
            
            logger.info("="*80)
            logger.info("=== 📝 RENDERING TEMPLATE WITH REASON MODAL ===")
            logger.info(f"   show_reason_form: True")
            logger.info(f"   detected_changes: {len(all_changes)} changes")
            logger.info("="*80)
            
            return render(request, 'studies/study_44en/CRF/individual/form.html', context)
        
        # ===================================
        # STEP 5: SAVE WITH AUDIT
        # ===================================
        sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
        
        # Log the changes and reasons
        logger.info("="*80)
        logger.info("📋 AUDIT TRAIL:")
        logger.info(f"   User: {request.user.username}")
        logger.info(f"   Changes: {len(all_changes)}")
        for change in all_changes:
            reason = sanitized_reasons.get(change['field'], 'N/A')
            logger.info(f"      - {change['field']}: {change['old_value']} → {change['new_value']}")
            logger.info(f"        Reason: {reason}")
        logger.info("="*80)
        
        # Set audit_data for decorator
        combined_reason = "\n".join([
            f"{change['field']}: {sanitized_reasons.get(change['field'], 'N/A')}"
            for change in all_changes
        ])
        
        request.audit_data = {
            'patient_id': subjectid,
            'site_id': getattr(individual, 'SITEID', None),
            'reason': combined_reason,
            'changes': all_changes,
            'reasons_json': sanitized_reasons,
        }
        
        individual = save_individual(
            request=request,
            individual_form=individual_form,
            is_create=False,
            change_reasons=sanitized_reasons,  # Pass reasons for audit log
            all_changes=all_changes  # Pass change details for audit log
        )
        
        if individual:
            logger.info("="*80)
            logger.info(f"=== INDIVIDUAL UPDATE SUCCESS: {individual.SUBJECTID} ===")
            logger.info("="*80)
            
            messages.success(request, f'Cập nhật individual {individual.SUBJECTID} thành công!')
            return redirect('study_44en:individual:detail', subjectid=individual.SUBJECTID)
        else:
            logger.error("❌ Save failed")
            messages.error(request, 'Lỗi khi lưu dữ liệu')
    else:
        # Log validation errors
        logger.error("❌ Form validation failed")
        log_form_errors(individual_form, 'Individual Form')
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # Re-render with errors
    context = {
        'individual_form': individual_form,
        'individual': individual,
        'is_create': False,
        'is_readonly': False,
        'today': date.today(),
        'current_version': individual.version if hasattr(individual, 'version') else None,
    }
    
    logger.info("="*80)
    logger.info("=== 📝 INDIVIDUAL UPDATE END (POST) - Rendering with errors ===")
    logger.info("="*80)
    
    return render(request, 'studies/study_44en/CRF/individual/form.html', context)


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('individual')
def individual_view(request, subjectid):
    """
    View individual (read-only mode)
    """
    logger.info("="*80)
    logger.info(f"=== 👁️ INDIVIDUAL VIEW (READ-ONLY): {subjectid} ===")
    logger.info("="*80)
    
    # Use helper to get individual
    individual = get_individual_with_related(request, subjectid)
    
    # Create readonly form
    individual_form = IndividualForm(instance=individual)
    
    # Use helper to make form readonly
    make_form_readonly(individual_form)
    
    logger.info(f"   Form made readonly")
    
    context = {
        'individual_form': individual_form,
        'individual': individual,
        'is_create': False,
        'is_readonly': True,
        'today': date.today(),
    }
    
    logger.info("="*80)
    logger.info("=== 👁️ INDIVIDUAL VIEW END - Rendering template ===")
    logger.info("="*80)
    
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


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'individual_list',
    'individual_detail',
    'individual_create',
    'individual_update',
    'individual_view',
    'individual_edit',  # Deprecated
]
