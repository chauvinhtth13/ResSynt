# backends/studies/study_43en/views/patient/sample/views_sample.py
"""
Sample Collection CRUD Views - REFACTORED with Universal Audit System
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

# Import forms
from backends.studies.study_43en.forms.patient.SAM import SampleCollectionForm

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
    SAM_CASE
)
from backends.studies.study_43en.models import AuditLog, AuditLogDetail

# Import audit utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import (
    process_crf_update,
    process_crf_create,
)

# Import permission utilities
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)
from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_enrollment_with_samples(request, usubjid):
    """Get enrollment and related samples"""
    # Get site filtering parameters FIRST
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get screening case with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    
    # Get enrollment case with site filtering
    enrollment_case = get_site_filtered_object_or_404(
        ENR_CASE, site_filter, filter_type, USUBJID=screening_case
    )
    
    # Get samples (no filtering needed - already filtered by enrollment)
    samples = SAM_CASE.objects.filter(USUBJID=enrollment_case).order_by('SAMPLE_TYPE')
    
    return screening_case, enrollment_case, samples


def validate_sample_type(sample_type):
    """Validate sample type"""
    valid_types = [choice[0] for choice in SAM_CASE.SampleTypeChoices.choices]
    return sample_type in valid_types


def check_sample_exists(enrollment_case, sample_type):
    """Check if sample already exists"""
    return SAM_CASE.objects.filter(
        USUBJID=enrollment_case,
        SAMPLE_TYPE=sample_type
    ).exists()


def get_single_sample(enrollment_case, sample_type):
    """Get single sample or None"""
    try:
        return SAM_CASE.objects.get(
            USUBJID=enrollment_case,
            SAMPLE_TYPE=sample_type
        )
    except SAM_CASE.DoesNotExist:
        return None


# ==========================================
# LIST VIEW
# ==========================================

@login_required
@require_crf_view('sam_case', redirect_to='study_43en:patient_list')
def sample_collection_list(request, usubjid):
    """
    Display list of sample collections for a patient
    
    Permission: view_samplecollection
    """
    logger.info(f"=== SAMPLE COLLECTION LIST ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get data
    screening_case, enrollment_case, samples = get_enrollment_with_samples(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Check view mode
    mode = request.GET.get('mode', 'edit')
    is_view_only = mode == 'view'
    
    # Prepare data
    sample_types = SAM_CASE.SampleTypeChoices.choices
    samples_by_type = {sample.SAMPLE_TYPE: sample for sample in samples}
    
    context = {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'sample_types': sample_types,
        'samples': samples,
        'samples_by_type': samples_by_type,
        'is_view_only': is_view_only,
        'selected_site_id': screening_case.SITEID,
    }
    
    logger.info(f" Loaded {samples.count()} samples")
    
    return render(request, 'studies/study_43en/patient/list/sample_collection_list.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('sam_case', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='SAMPLECOLLECTION',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def sample_collection_create(request, usubjid, sample_type):
    """
    Create new sample collection (NO AUDIT)
    
    Permission: add_samplecollection
    """
    logger.info(f"=== SAMPLE COLLECTION CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Type: {sample_type}")
    
    # Validate sample type
    if not validate_sample_type(sample_type):
        messages.error(request, f' Sample type không hợp lệ: {sample_type}')
        return redirect('study_43en:sample_collection_list', usubjid=usubjid)
    
    # Get enrollment
    screening_case, enrollment_case, _ = get_enrollment_with_samples(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if already exists
    if check_sample_exists(enrollment_case, sample_type):
        logger.info(f" Sample exists, redirecting to update")
        messages.info(request, f'Mẫu {sample_type} đã tồn tại. Chuyển sang cập nhật.')
        return redirect('study_43en:sample_collection_update',
                       usubjid=usubjid, sample_type=sample_type)
    
    # Pre-save callback
    def pre_save(instance):
        instance.USUBJID = enrollment_case
        instance.SAMPLE_TYPE = sample_type
    
    # POST - Create form with patient parameter
    if request.method == 'POST':
        form = SampleCollectionForm(
            request.POST, 
            request.FILES,
            patient=enrollment_case,
            initial={'SAMPLE_TYPE': sample_type}
        )
        
        if not form.is_valid():
            logger.error(f" Form validation failed: {form.errors}")
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi!')
            
            context = {
                'form': form,
                'sample': None,
                'screening_case': screening_case,
                'enrollment_case': enrollment_case,
                'usubjid': usubjid,
                'sample_type': sample_type,
                'sample_type_display': dict(SAM_CASE.SampleTypeChoices.choices).get(sample_type, sample_type),
                'is_create': True,
                'is_readonly': False,
                'selected_site_id': screening_case.SITEID,
            }
            
            return render(request, 'studies/study_43en/patient/form/sample_collection_form.html', context)
        
        # Save with pre-save callback
        try:
            logger.info(" Form valid, creating...")
            
            with transaction.atomic():
                instance = form.save(commit=False)
                pre_save(instance)
                
                # Set metadata
                if hasattr(instance, 'version'):
                    instance.version = 0
                
                if hasattr(instance, 'last_modified_by_id'):
                    instance.last_modified_by_id = request.user.id
                
                if hasattr(instance, 'last_modified_by_username'):
                    instance.last_modified_by_username = request.user.username
                
                instance.save()
                
                logger.info(f" Created successfully!")
            
            messages.success(request, 'Tạo mới mẫu thành công!')
            return redirect('study_43en:sample_collection_list', usubjid=usubjid)
            
        except Exception as e:
            logger.error(f" Error saving: {e}", exc_info=True)
            messages.error(request, f'Lỗi khi lưu: {str(e)}')
            
            context = {
                'form': form,
                'sample': None,
                'screening_case': screening_case,
                'enrollment_case': enrollment_case,
                'usubjid': usubjid,
                'sample_type': sample_type,
                'sample_type_display': dict(SAM_CASE.SampleTypeChoices.choices).get(sample_type, sample_type),
                'is_create': True,
                'is_readonly': False,
                'selected_site_id': screening_case.SITEID,
            }
            
            return render(request, 'studies/study_43en/patient/form/sample_collection_form.html', context)
    
    # GET - Show blank form
    logger.info(" Showing blank form")
    form = SampleCollectionForm(patient=enrollment_case, initial={'SAMPLE_TYPE': sample_type})
    
    context = {
        'form': form,
        'sample': None,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'sample_type_display': dict(SAM_CASE.SampleTypeChoices.choices).get(sample_type, sample_type),
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_case.SITEID,
    }
    
    return render(request, 'studies/study_43en/patient/form/sample_collection_form.html', context)


# ==========================================
# UPDATE VIEW WITH AUDIT
# ==========================================

@login_required
@require_crf_change('sam_case', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='SAMPLECOLLECTION',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def sample_collection_update(request, usubjid, sample_type):
    """
    Update sample collection WITH UNIVERSAL AUDIT SYSTEM (Tier 1)
    
    Permission: change_samplecollection
    """
    logger.info(f"=== SAMPLE COLLECTION UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Type: {sample_type}, Method: {request.method}")
    
    # Validate sample type
    if not validate_sample_type(sample_type):
        messages.error(request, f' Sample type không hợp lệ: {sample_type}')
        return redirect('study_43en:sample_collection_list', usubjid=usubjid)
    
    # Get enrollment and sample
    screening_case, enrollment_case, _ = get_enrollment_with_samples(request,usubjid)
    sample = get_single_sample(enrollment_case, sample_type)
    
    if not sample:
        messages.error(request, f' Không tìm thấy mẫu {sample_type}')
        return redirect('study_43en:sample_collection_list', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        form = SampleCollectionForm(instance=sample, patient=enrollment_case)
        
        context = {
            'form': form,
            'sample': sample,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'sample_type_display': dict(SAM_CASE.SampleTypeChoices.choices).get(sample_type, sample_type),
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': screening_case.SITEID,
            'current_version': sample.version,
        }
        
        return render(request, 'studies/study_43en/patient/form/sample_collection_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 1)
    logger.info(" Using Universal Audit System (Tier 1)")
    
    #  Form tự động detect patient từ instance - không cần wrapper class
    return process_crf_update(
        request=request,
        instance=sample,
        form_class=SampleCollectionForm,  # ← Dùng trực tiếp, form tự detect patient
        template_name='studies/study_43en/patient/form/sample_collection_form.html',
        redirect_url=reverse('study_43en:sample_collection_list', kwargs={'usubjid': usubjid}),
        extra_context={
            'sample': sample,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'sample_type_display': dict(SAM_CASE.SampleTypeChoices.choices).get(sample_type, sample_type),
            'selected_site_id': screening_case.SITEID,
            'current_version': sample.version,
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('sam_case', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='SAMPLECOLLECTION',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def sample_collection_view(request, usubjid, sample_type):
    """
    View sample in read-only mode
    
    Permission: view_samplecollection
    
    CRITICAL: This view BLOCKS all POST requests for security
    """
    logger.info(f"=== SAMPLE COLLECTION VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Type: {sample_type}, Method: {request.method}")
    
    #  BLOCK POST requests in readonly mode
    if request.method == 'POST':
        logger.warning(f"POST attempt blocked in readonly mode by {request.user.username}")
        messages.error(request, 'Chế độ chỉ xem - không thể chỉnh sửa!')
        return redirect('study_43en:sample_collection_view', usubjid=usubjid, sample_type=sample_type)
    
    # Validate sample type
    if not validate_sample_type(sample_type):
        messages.error(request, f' Sample type không hợp lệ: {sample_type}')
        return redirect('study_43en:sample_collection_list', usubjid=usubjid)
    
    # Get data
    screening_case, enrollment_case, _ = get_enrollment_with_samples(request, usubjid)
    sample = get_single_sample(enrollment_case, sample_type)
    
    if not sample:
        messages.error(request, f' Không tìm thấy mẫu {sample_type}')
        return redirect('study_43en:sample_collection_list', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    #  Create READONLY form with all fields disabled
    form = SampleCollectionForm(instance=sample, patient=enrollment_case)
    
    #  FORCE disable ALL fields (không thể bỏ qua bằng JavaScript)
    for field_name, field in form.fields.items():
        field.disabled = True
        field.required = False
        field.widget.attrs.update({
            'readonly': 'readonly',
            'disabled': 'disabled',
            'style': 'pointer-events: none; background-color: #f3f4f6;'
        })
    
    context = {
        'form': form,
        'sample': sample,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'sample_type_display': dict(SAM_CASE.SampleTypeChoices.choices).get(sample_type, sample_type),
        'is_create': False,
        'is_readonly': True, 
        'is_view_only': True, 
        'selected_site_id': screening_case.SITEID,
        'current_version': sample.version,
    }
    
    logger.info(f" Readonly mode active - all modifications blocked")
    
    return render(request, 'studies/study_43en/patient/form/sample_collection_form.html', context)
