"""
Discharge CRUD Views - REFACTORED with Universal Audit System
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

#  FIXED IMPORTS
from backends.studies.study_43en.forms.patient.DISCH import (
    DischargeCaseForm,
    DischargeICDFormSet,
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

# Import helpers
from .helpers import (
    get_discharge_with_related,
    save_discharge_and_related,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('disch_case', redirect_to='study_43en:patient_list')
@audit_log(model_name='DISCHARGECASE', get_patient_id_from='usubjid')
def discharge_create(request, usubjid):
    """
    Create new discharge case (NO AUDIT)
    
    Permission: add_dischargecase
    """
    logger.info(f"=== DISCHARGE CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if discharge exists
    screening_case, enrollment_case, discharge_case = get_discharge_with_related(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if discharge already exists
    if discharge_case:
        messages.info(request, f'Bệnh nhân {usubjid} đã có thông tin xuất viện.')
        return redirect('study_43en:discharge_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        # Initialize all forms with patient context
        discharge_form = DischargeCaseForm(request.POST, patient=enrollment_case)
        icd_formset = DischargeICDFormSet(  #  Use correct name
            request.POST,
            prefix='icd',
            queryset=enrollment_case.discharge_case.icd_codes.none() if hasattr(enrollment_case, 'discharge_case') else None
        )
        
        # Validate
        all_valid = all([
            discharge_form.is_valid(),
            icd_formset.is_valid()
        ])
        
        if all_valid:
            forms_dict = {
                'discharge_form': discharge_form,
                'icd_formset': icd_formset,
            }
            
            discharge = save_discharge_and_related(
                request=request,
                enrollment_case=enrollment_case,
                is_create=True,
                **forms_dict
            )
            
            if discharge:
                messages.success(
                    request,
                    f' Đã tạo thông tin xuất viện cho bệnh nhân {usubjid} thành công.'
                )
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            # Show errors
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        discharge_form = DischargeCaseForm(patient=enrollment_case)
        icd_formset = DischargeICDFormSet(  #  Use correct name
            prefix='icd',
            queryset=enrollment_case.discharge_case.icd_codes.none() if hasattr(enrollment_case, 'discharge_case') else None
        )
    
    context = {
        'discharge_form': discharge_form,
        'icd_formset': icd_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'discharge_case': None,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/CRF/patient/discharge_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('disch_case', redirect_to='study_43en:patient_list')
@audit_log(model_name='DISCHARGECASE', get_patient_id_from='usubjid')
def discharge_update(request, usubjid):
    """
    Update discharge case WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Permission: change_dischargecase
    """
    logger.info(f"=== DISCHARGE UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get discharge with related data
    screening_case, enrollment_case, discharge_case = get_discharge_with_related(request,usubjid)
    
    if not discharge_case:
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có thông tin xuất viện.')
        return redirect('study_43en:discharge_create', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        discharge_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        discharge_form = DischargeCaseForm(instance=discharge_case, patient=enrollment_case)
        icd_formset = DischargeICDFormSet(  #  Use correct name
            instance=discharge_case,
            prefix='icd'
        )
        
        context = {
            'discharge_form': discharge_form,
            'icd_formset': icd_formset,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'discharge_case': discharge_case,
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': screening_case.SITEID,
            'today': date.today(),
            'current_version': discharge_case.version,
        }
        
        return render(request, 'studies/study_43en/CRF/patient/discharge_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info(" Using Universal Audit System (Tier 3)")
    
    # Configure forms
    forms_config = {
        'main': {
            'class': DischargeCaseForm,
            'instance': discharge_case
        },
        'formsets': {
            'icd_codes': {
                'class': DischargeICDFormSet,  #  Use correct name
                'instance': discharge_case,
                'prefix': 'icd',
                'related_name': 'icd_codes'
            }
        }
    }
    
    # Define save callback
    def save_callback(request, forms_dict):
        # Map forms_dict to expected format
        mapped_forms = {
            'discharge_form': forms_dict['main'],
            'icd_formset': forms_dict['formsets']['icd_codes'],
        }
        
        return save_discharge_and_related(
            request=request,
            enrollment_case=enrollment_case,
            is_create=False,
            **mapped_forms
        )
    
    # Use Universal Audit System
    return process_complex_update(
        request=request,
        main_instance=discharge_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/CRF/patient/discharge_form.html',
        redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'discharge_case': discharge_case,
            'selected_site_id': screening_case.SITEID,
            'today': date.today(),
            'current_version': discharge_case.version,
        }
    )


# ==========================================
# READ-ONLY VIEW
# ==========================================

@login_required
@require_crf_view('disch_case', redirect_to='study_43en:patient_list')
@audit_log(model_name='DISCHARGECASE', get_patient_id_from='usubjid')
def discharge_view(request, usubjid):
    """
    View discharge case (read-only)
    
    Permission: view_dischargecase
    """
    logger.info(f"=== DISCHARGE VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get discharge with related data
    screening_case, enrollment_case, discharge_case = get_discharge_with_related(request,usubjid)
    
    if not discharge_case:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin xuất viện.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        discharge_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Create read-only forms
    discharge_form = DischargeCaseForm(instance=discharge_case)
    icd_formset = DischargeICDFormSet(  #  Use correct name
        instance=discharge_case,
        prefix='icd'
    )
    
    # Make everything readonly
    make_form_readonly(discharge_form)
    make_formset_readonly(icd_formset)
    
    context = {
        'discharge_form': discharge_form,
        'icd_formset': icd_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'discharge_case': discharge_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/CRF/patient/discharge_form.html', context)