# backends/studies/study_43en/views/patient/endcase/views_endcase.py
"""
End Case CRF CRUD Views - REFACTORED with Universal Audit System
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import forms
from backends.studies.study_43en.forms.patient.ENDCASE import EndCaseCRFForm

# Import utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import (
    process_crf_update,
    process_crf_create,
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
    get_endcase_with_related,
    make_form_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('endcasecrf', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='ENDCASECRF',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def endcase_create(request, usubjid):
    """
    Create new end case CRF (NO AUDIT)
    
    Permission: add_endcasecrf
    """
    logger.info(f"=== END CASE CRF CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if end case exists
    screening_case, enrollment_case, endcase = get_endcase_with_related(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if end case already exists
    if endcase:
        messages.info(request, f'Bệnh nhân {usubjid} đã có phiếu kết thúc nghiên cứu.')
        return redirect('study_43en:endcase_update', usubjid=usubjid)
    
    # Pre-save callback
    def pre_save(instance):
        instance.USUBJID = enrollment_case
    
    # POST - Use universal create processor
    if request.method == 'POST':
        return process_crf_create(
            request=request,
            form_class=EndCaseCRFForm,
            template_name='studies/study_43en/patient/form/endcase_form.html',
            redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
            pre_save_callback=pre_save,
            extra_context={
                'endcase': None,
                'screening_case': screening_case,
                'enrollment_case': enrollment_case,
                'selected_site_id': screening_case.SITEID,
            }
        )
    
    # GET - Show blank form with smart defaults
    logger.info(" Showing blank form")
    
    initial_data = {
        'ENDDATE': date.today(),
        'ENDFORMDATE': date.today(),
        'WITHDRAWREASON': 'na',
        'INCOMPLETE': 'na',
        'LOSTTOFOLLOWUP': 'na',
    }
    
    form = EndCaseCRFForm(
        initial=initial_data,
        patient=enrollment_case
    )
    
    context = {
        'form': form,
        'endcase': None,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/patient/form/endcase_form.html', context)


# ==========================================
# UPDATE VIEW WITH AUDIT
# ==========================================

@login_required
@require_crf_change('endcasecrf', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='ENDCASECRF',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def endcase_update(request, usubjid):
    """
    Update end case CRF WITH UNIVERSAL AUDIT SYSTEM (Tier 1)
    
    Permission: change_endcasecrf
    """
    logger.info(f"=== END CASE CRF UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get end case with related data
    screening_case, enrollment_case, endcase = get_endcase_with_related(request,usubjid)
    
    if not endcase:
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có phiếu kết thúc nghiên cứu.')
        return redirect('study_43en:endcase_create', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        endcase,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        form = EndCaseCRFForm(
            instance=endcase,
            patient=enrollment_case
        )
        
        context = {
            'form': form,
            'endcase': endcase,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': screening_case.SITEID,
            'today': date.today(),
            'current_version': endcase.version,
        }
        
        return render(request, 'studies/study_43en/patient/form/endcase_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 1)
    logger.info(" Using Universal Audit System (Tier 1)")
    
    #  Form tự động detect patient từ instance
    return process_crf_update(
        request=request,
        instance=endcase,
        form_class=EndCaseCRFForm,
        template_name='studies/study_43en/patient/form/endcase_form.html',
        redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'endcase': endcase,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'selected_site_id': screening_case.SITEID,
            'current_version': endcase.version,
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('endcasecrf', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='ENDCASECRF',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def endcase_view(request, usubjid):
    """
    View end case CRF in read-only mode
    
    Permission: view_endcasecrf
    """
    logger.info(f"=== END CASE CRF VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get end case with related data
    screening_case, enrollment_case, endcase = get_endcase_with_related(request,usubjid)
    
    if not endcase:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có phiếu kết thúc nghiên cứu.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        endcase,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Create read-only form
    form = EndCaseCRFForm(
        instance=endcase,
        patient=enrollment_case
    )
    
    # Make all fields readonly
    make_form_readonly(form)
    
    context = {
        'form': form,
        'endcase': endcase,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/patient/form/endcase_form.html', context)
