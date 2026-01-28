# backends/studies/study_43en/views/patient/FU90/views_fu_90.py
"""
Follow-up Day 90 CRUD Views - REFACTORED with Universal Audit System
 UPDATED: Field names match new models
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import forms
from backends.studies.study_43en.forms.patient.FU_90 import (
    FollowUpCase90Form,
    Rehospitalization90FormSet,
    FollowUpAntibiotic90FormSet,
)

# Import utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import (
    process_complex_update,
)
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)

# Import models for audit
from backends.studies.study_43en.models.patient import SCR_CASE
from backends.studies.study_43en.models import AuditLog, AuditLogDetail

# Import helpers
from .helpers import (
    get_followup90_with_related,
    save_followup90_and_related,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('fu_case_90', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='FOLLOWUPCASE90',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def followup_90_create(request, usubjid):
    """
    Create new follow-up Day 90 (NO AUDIT)
    
    Permission: add_followupcase90
    """
    logger.info(f"=== FOLLOW-UP DAY 90 CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if follow-up exists
    screening_case, enrollment_case, followup_case = get_followup90_with_related(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if follow-up already exists
    if followup_case:
        messages.info(request, f'Bệnh nhân {usubjid} đã có thông tin theo dõi Day 90.')
        return redirect('study_43en:followup_90_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        # Initialize all forms
        followup_form = FollowUpCase90Form(request.POST, enrollment_case=enrollment_case)
        
        #  UPDATED: Use instance=None for create
        rehospitalization_formset = Rehospitalization90FormSet(
            request.POST,
            prefix='rehospitalization90',
            instance=None  #  For create, always None
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            request.POST,
            prefix='antibiotic90',
            instance=None  #  For create, always None
        )
        
        # Validate
        all_valid = all([
            followup_form.is_valid(),
            rehospitalization_formset.is_valid(),
            antibiotic_formset.is_valid()
        ])
        
        if all_valid:
            forms_dict = {
                'followup_form': followup_form,
                'rehospitalization_formset': rehospitalization_formset,
                'antibiotic_formset': antibiotic_formset,
            }
            
            followup = save_followup90_and_related(
                request=request,
                enrollment_case=enrollment_case,
                is_create=True,
                **forms_dict
            )
            
            if followup:
                messages.success(
                    request,
                    f' Đã tạo thông tin theo dõi Day 90 cho bệnh nhân {usubjid} thành công.'
                )
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        followup_form = FollowUpCase90Form(enrollment_case=enrollment_case)
        rehospitalization_formset = Rehospitalization90FormSet(
            prefix='rehospitalization90',
            instance=None  #  For create, always None
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            prefix='antibiotic90',
            instance=None  #  For create, always None
        )
    
    context = {
        'followup_form': followup_form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'followup_case': None,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/patient/form/followup_90_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('fu_case_90', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='FOLLOWUPCASE90',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def followup_90_update(request, usubjid):
    """
    Update follow-up Day 90 WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Permission: change_followupcase90
    """
    logger.info(f"=== FOLLOW-UP DAY 90 UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    screening_case, enrollment_case, followup_case = get_followup90_with_related(request,usubjid)
    
    if not followup_case:
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi Day 90.')
        return redirect('study_43en:followup_90_create', usubjid=usubjid)
    
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        followup_form = FollowUpCase90Form(instance=followup_case)
        rehospitalization_formset = Rehospitalization90FormSet(
            instance=followup_case,
            prefix='rehospitalization90'
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            instance=followup_case,
            prefix='antibiotic90'
        )
        
        context = {
            'followup_form': followup_form,
            'rehospitalization_formset': rehospitalization_formset,
            'antibiotic_formset': antibiotic_formset,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'followup_case': followup_case,
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': screening_case.SITEID,
            'today': date.today(),
            'current_version': followup_case.version,
        }
        
        return render(request, 'studies/study_43en/patient/form/followup_90_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info(" Using Universal Audit System (Tier 3)")
    
    # Configure forms
    forms_config = {
        'main': {
            'class': FollowUpCase90Form,
            'instance': followup_case
        },
        'formsets': {
            'rehospitalizations': {
                'class': Rehospitalization90FormSet,
                'instance': followup_case,
                'prefix': 'rehospitalization90',
                'related_name': 'rehospitalizations'
            },
            'antibiotics': {
                'class': FollowUpAntibiotic90FormSet,
                'instance': followup_case,
                'prefix': 'antibiotic90',
                'related_name': 'antibiotics'
            }
        }
    }
    
    # Define save callback
    def save_callback(request, forms_dict):
        # Map forms_dict to expected format
        mapped_forms = {
            'followup_form': forms_dict['main'],
            'rehospitalization_formset': forms_dict['formsets']['rehospitalizations'],
            'antibiotic_formset': forms_dict['formsets']['antibiotics'],
        }
        
        return save_followup90_and_related(
            request=request,
            enrollment_case=enrollment_case,
            is_create=False,
            **mapped_forms
        )
    
    # Use Universal Audit System
    return process_complex_update(
        request=request,
        main_instance=followup_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/patient/form/followup_90_form.html',
        redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'followup_case': followup_case,
            'selected_site_id': screening_case.SITEID,
            'today': date.today(),
            'current_version': followup_case.version,
        }
    )


# ==========================================
# READ-ONLY VIEW
# ==========================================

@login_required
@require_crf_view('fu_case_90', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='FOLLOWUPCASE90',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def followup_90_view(request, usubjid):
    """
    View follow-up Day 90 (read-only)
    
    Permission: view_followupcase90
    """
    logger.info(f"=== FOLLOW-UP DAY 90 VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    screening_case, enrollment_case, followup_case = get_followup90_with_related(request,usubjid)
    
    if not followup_case:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi Day 90.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    followup_form = FollowUpCase90Form(instance=followup_case)
    rehospitalization_formset = Rehospitalization90FormSet(
        instance=followup_case,
        prefix='rehospitalization90'
    )
    antibiotic_formset = FollowUpAntibiotic90FormSet(
        instance=followup_case,
        prefix='antibiotic90'
    )
    
    make_form_readonly(followup_form)
    make_formset_readonly(rehospitalization_formset)
    make_formset_readonly(antibiotic_formset)
    
    context = {
        'followup_form': followup_form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'followup_case': followup_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/patient/form/followup_90_form.html', context)
