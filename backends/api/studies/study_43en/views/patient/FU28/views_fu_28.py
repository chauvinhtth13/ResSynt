# backends/studies/study_43en/views/patient/FU28/views_fu_28.py
"""
Follow-up Day 28 CRUD Views - REFACTORED with Universal Audit System
 UPDATED: Field names match new models
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import forms
from backends.studies.study_43en.forms.patient.FU_28 import (
    FollowUpCaseForm,
    RehospitalizationFormSet,
    FollowUpAntibioticFormSet,
)

# Import utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import (
    process_complex_update,
    process_crf_create,
)
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)

# Import helpers
from .helpers import (
    get_followup_with_related,
    save_followup_and_related,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('fu_case_28', redirect_to='study_43en:patient_list')
@audit_log(model_name='FOLLOWUPCASE', get_patient_id_from='usubjid')
def followup_28_create(request, usubjid):
    """
    Create new follow-up Day 28 (NO AUDIT)
    
    Permission: add_followupcase
    """
    logger.info(f"=== FOLLOW-UP DAY 28 CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if follow-up exists
    screening_case, enrollment_case, followup_case = get_followup_with_related(request, usubjid)
    
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
        messages.info(request, f'Bệnh nhân {usubjid} đã có thông tin theo dõi Day 28.')
        return redirect('study_43en:followup_28_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        # Initialize all forms
        followup_form = FollowUpCaseForm(request.POST)
        
        #  UPDATED: Use new related_name 'followup_28' instead of checking hasattr
        rehospitalization_formset = RehospitalizationFormSet(
            request.POST,
            prefix='rehospitalization',
            instance=None  #  For create, always None
        )
        antibiotic_formset = FollowUpAntibioticFormSet(
            request.POST,
            prefix='antibiotic',
            instance=None  #  For create, always None
        )
        
        # Validate all forms
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
            
            followup = save_followup_and_related(
                request=request,
                enrollment_case=enrollment_case,
                is_create=True,
                **forms_dict
            )
            
            if followup:
                messages.success(
                    request,
                    f' Đã tạo thông tin theo dõi Day 28 cho bệnh nhân {usubjid} thành công.'
                )
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            # Show errors
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        followup_form = FollowUpCaseForm()
        rehospitalization_formset = RehospitalizationFormSet(
            prefix='rehospitalization',
            instance=None  #  For create, always None
        )
        antibiotic_formset = FollowUpAntibioticFormSet(
            prefix='antibiotic',
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
    
    return render(request, 'studies/study_43en/CRF/patient/followup_28_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('fu_case_28', redirect_to='study_43en:patient_list')
@audit_log(model_name='FOLLOWUPCASE', get_patient_id_from='usubjid')
def followup_28_update(request, usubjid):
    """
    Update follow-up Day 28 WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Permission: change_followupcase
    """
    logger.info(f"=== FOLLOW-UP DAY 28 UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get follow-up with related data
    screening_case, enrollment_case, followup_case = get_followup_with_related(request, usubjid)
    
    if not followup_case:
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi Day 28.')
        return redirect('study_43en:followup_28_create', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        followup_form = FollowUpCaseForm(instance=followup_case)
        rehospitalization_formset = RehospitalizationFormSet(
            instance=followup_case,
            prefix='rehospitalization'
        )
        antibiotic_formset = FollowUpAntibioticFormSet(
            instance=followup_case,
            prefix='antibiotic'
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
        
        return render(request, 'studies/study_43en/CRF/patient/followup_28_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info(" Using Universal Audit System (Tier 3)")
    
    # Configure forms
    forms_config = {
        'main': {
            'class': FollowUpCaseForm,
            'instance': followup_case
        },
        'formsets': {
            'rehospitalizations': {
                'class': RehospitalizationFormSet,
                'instance': followup_case,
                'prefix': 'rehospitalization',
                'related_name': 'rehospitalizations'
            },
            'antibiotics': {
                'class': FollowUpAntibioticFormSet,
                'instance': followup_case,
                'prefix': 'antibiotic',
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
        
        return save_followup_and_related(
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
        template_name='studies/study_43en/CRF/patient/followup_28_form.html',
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
@require_crf_view('fu_case_28', redirect_to='study_43en:patient_list')
@audit_log(model_name='FOLLOWUPCASE', get_patient_id_from='usubjid')
def followup_28_view(request, usubjid):
    """
    View follow-up Day 28 (read-only)
    
    Permission: view_followupcase
    """
    logger.info(f"=== FOLLOW-UP DAY 28 VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get follow-up with related data
    screening_case, enrollment_case, followup_case = get_followup_with_related(request, usubjid)
    
    if not followup_case:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi Day 28.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Create read-only forms
    followup_form = FollowUpCaseForm(instance=followup_case)
    rehospitalization_formset = RehospitalizationFormSet(
        instance=followup_case,
        prefix='rehospitalization'
    )
    antibiotic_formset = FollowUpAntibioticFormSet(
        instance=followup_case,
        prefix='antibiotic'
    )
    
    # Make everything readonly
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
    
    return render(request, 'studies/study_43en/CRF/patient/followup_28_form.html', context)