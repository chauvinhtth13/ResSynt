# backends/studies/study_43en/views/contact/FU90/views_contact_fu_90.py
"""
Contact Follow-up Day 90 CRUD Views - REFACTORED with Universal Audit System
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
# Import models
from backends.studies.study_43en.models.contact import ContactMedicationHistory90
# Import forms
from backends.studies.study_43en.forms.contact.contact_FU_90 import (
    ContactFollowUp90Form,
    ContactMedicationHistory90FormSet,
)

# Import utilities
from backends.audit_log.utils.decorators import audit_log
from backends.audit_log.utils.processors import (
    process_complex_update,
)
from backends.audit_log.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)

# Import helpers
from .helpers import (
    get_contact_followup90_with_related,
    save_contact_followup90_and_related,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('fu_contact_90', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTFOLLOWUP90', get_patient_id_from='usubjid')
def contact_followup_90_create(request, usubjid):
    """
    Create new contact follow-up Day 90 (NO AUDIT)
    
    Permission: add_contactfollowup90
    """
    logger.info(f"=== CONTACT FOLLOW-UP DAY 90 CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if follow-up exists
    enrollment_contact, followup_case = get_contact_followup90_with_related(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_contact,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if follow-up already exists
    if followup_case:
        messages.info(request, f'Người tiếp xúc {usubjid} đã có thông tin theo dõi Day 90.')
        return redirect('study_43en:contact_followup_90_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        # Initialize all forms
        followup_form = ContactFollowUp90Form(request.POST)
        medication_formset = ContactMedicationHistory90FormSet(
            request.POST,
            prefix='medication90',
            queryset=ContactMedicationHistory90.objects.none()
        )
        
        # Validate
        all_valid = all([
            followup_form.is_valid(),
            medication_formset.is_valid()
        ])
        
        if all_valid:
            forms_dict = {
                'followup_form': followup_form,
                'medication_formset': medication_formset,
            }
            
            followup = save_contact_followup90_and_related(
                request=request,
                enrollment_contact=enrollment_contact,
                is_create=True,
                **forms_dict
            )
            
            if followup:
                messages.success(
                    request,
                    f' Đã tạo thông tin theo dõi Day 90 cho người tiếp xúc {usubjid} thành công.'
                )
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        followup_form = ContactFollowUp90Form()
        medication_formset = ContactMedicationHistory90FormSet(
            prefix='medication90',
            queryset=ContactMedicationHistory90.objects.none()
        )
    
    context = {
        'followup_form': followup_form,
        'medication_formset': medication_formset,
        'enrollment_contact': enrollment_contact,
        'followup_case': None,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': enrollment_contact.SITEID,
        'today': date.today(),
        'followup_type': '90',
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_followup_90.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('fu_contact_90', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTFOLLOWUP90', get_patient_id_from='usubjid')
def contact_followup_90_update(request, usubjid):
    """
    Update contact follow-up Day 90 WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Permission: change_contactfollowup90
    """
    logger.info(f"=== CONTACT FOLLOW-UP DAY 90 UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    enrollment_contact, followup_case = get_contact_followup90_with_related(request,usubjid)
    
    if not followup_case:
        messages.warning(request, f'Người tiếp xúc {usubjid} chưa có thông tin theo dõi Day 90.')
        return redirect('study_43en:contact_followup_90_create', usubjid=usubjid)
    
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        followup_form = ContactFollowUp90Form(instance=followup_case)
        medication_formset = ContactMedicationHistory90FormSet(
            instance=followup_case,
            prefix='medication90'
        )
        
        context = {
            'followup_form': followup_form,
            'medication_formset': medication_formset,
            'enrollment_contact': enrollment_contact,
            'followup_case': followup_case,
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': enrollment_contact.SITEID,
            'today': date.today(),
            'current_version': followup_case.version,
            'followup_type': '90',
        }
        
        return render(request, 'studies/study_43en/CRF/contact/contact_followup_90.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info(" Using Universal Audit System (Tier 3)")
    
    # Configure forms
    forms_config = {
        'main': {
            'class': ContactFollowUp90Form,
            'instance': followup_case
        },
        'formsets': {
            'medications': {
                'class': ContactMedicationHistory90FormSet,
                'instance': followup_case,
                'prefix': 'medication90',
                'related_name': 'medications'
            }
        }
    }
    
    # Define save callback
    def save_callback(request, forms_dict):
        # Map forms_dict to expected format
        mapped_forms = {
            'followup_form': forms_dict['main'],
            'medication_formset': forms_dict['formsets']['medications'],
        }
        
        return save_contact_followup90_and_related(
            request=request,
            enrollment_contact=enrollment_contact,
            is_create=False,
            **mapped_forms
        )
    
    # Use Universal Audit System
    return process_complex_update(
        request=request,
        main_instance=followup_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/CRF/contact/contact_followup_90.html',
        redirect_url=reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'enrollment_contact': enrollment_contact,
            'followup_case': followup_case,
            'selected_site_id': enrollment_contact.SITEID,
            'today': date.today(),
            'current_version': followup_case.version,
            'followup_type': '90',
        }
    )


# ==========================================
# READ-ONLY VIEW
# ==========================================

@login_required
@require_crf_view('fu_contact_90', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTFOLLOWUP90', get_patient_id_from='usubjid')
def contact_followup_90_view(request, usubjid):
    """
    View contact follow-up Day 90 (read-only)
    
    Permission: view_contactfollowup90
    """
    logger.info(f"=== CONTACT FOLLOW-UP DAY 90 VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    enrollment_contact, followup_case = get_contact_followup90_with_related(request,usubjid)
    
    if not followup_case:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin theo dõi Day 90.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    followup_form = ContactFollowUp90Form(instance=followup_case)
    medication_formset = ContactMedicationHistory90FormSet(
        instance=followup_case,
        prefix='medication90'
    )
    
    make_form_readonly(followup_form)
    make_formset_readonly(medication_formset)
    
    context = {
        'followup_form': followup_form,
        'medication_formset': medication_formset,
        'enrollment_contact': enrollment_contact,
        'followup_case': followup_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': enrollment_contact.SITEID,
        'today': date.today(),
        'followup_type': '90',
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_followup_90.html', context)
