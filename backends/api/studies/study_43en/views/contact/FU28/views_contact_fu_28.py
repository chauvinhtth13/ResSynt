# backends/studies/study_43en/views/contact/FU28/views_contact_fu_28.py
"""
Contact Follow-up Day 28 CRUD Views - REFACTORED with Universal Audit System
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import forms
from backends.studies.study_43en.forms.contact.contact_FU_28 import (
    ContactFollowUp28Form,
    ContactMedicationHistory28FormSet,
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
    get_contact_followup28_with_related,
    save_contact_followup28_and_related,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('fu_contact_28', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTFOLLOWUP28', get_patient_id_from='usubjid')
def contact_followup_28_create(request, usubjid):
    """
    Create new contact follow-up Day 28 (NO AUDIT)
    
    Permission: add_contactfollowup28
    """
    logger.info(f"=== CONTACT FOLLOW-UP DAY 28 CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if follow-up exists
    enrollment_contact, followup_case = get_contact_followup28_with_related(request,usubjid)
    
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
        messages.info(request, f'Người tiếp xúc {usubjid} đã có thông tin theo dõi Day 28.')
        return redirect('study_43en:contact_followup_28_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        # Initialize all forms
        followup_form = ContactFollowUp28Form(request.POST)
        medication_formset = ContactMedicationHistory28FormSet(
            request.POST,
            prefix='medication',
            queryset=followup_case.medications.none() if followup_case else None
        )
        
        # Validate all forms
        all_valid = all([
            followup_form.is_valid(),
            medication_formset.is_valid()
        ])
        
        if all_valid:
            forms_dict = {
                'followup_form': followup_form,
                'medication_formset': medication_formset,
            }
            
            followup = save_contact_followup28_and_related(
                request=request,
                enrollment_contact=enrollment_contact,
                is_create=True,
                **forms_dict
            )
            
            if followup:
                messages.success(
                    request,
                    f' Đã tạo thông tin theo dõi Day 28 cho người tiếp xúc {usubjid} thành công.'
                )
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            # Show errors
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        followup_form = ContactFollowUp28Form()
        medication_formset = ContactMedicationHistory28FormSet(
            prefix='medication',
            queryset=followup_case.medications.none() if followup_case else None
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
        'followup_type': '28',
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_followup_28.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('fu_contact_28', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTFOLLOWUP28', get_patient_id_from='usubjid')
def contact_followup_28_update(request, usubjid):
    """
    Update contact follow-up Day 28 WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Permission: change_contactfollowup28
    """
    logger.info(f"=== CONTACT FOLLOW-UP DAY 28 UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get follow-up with related data
    enrollment_contact, followup_case = get_contact_followup28_with_related(request,usubjid)
    
    if not followup_case:
        messages.warning(request, f'Người tiếp xúc {usubjid} chưa có thông tin theo dõi Day 28.')
        return redirect('study_43en:contact_followup_28_create', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        followup_form = ContactFollowUp28Form(instance=followup_case)
        medication_formset = ContactMedicationHistory28FormSet(
            instance=followup_case,
            prefix='medication'
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
            'followup_type': '28',
        }
        
        return render(request, 'studies/study_43en/CRF/contact/contact_followup_28.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info(" Using Universal Audit System (Tier 3)")
    
    #  FIX: Configure forms with correct queryset for CREATE scenario
    forms_config = {
        'main': {
            'class': ContactFollowUp28Form,
            'instance': followup_case
        },
        'formsets': {
            'medications': {
                'class': ContactMedicationHistory28FormSet,
                'instance': followup_case,  #  InlineFormSet pattern
                'prefix': 'medication',
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
        
        return save_contact_followup28_and_related(
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
        template_name='studies/study_43en/CRF/contact/contact_followup_28.html',
        redirect_url=reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'enrollment_contact': enrollment_contact,
            'followup_case': followup_case,
            'selected_site_id': enrollment_contact.SITEID,
            'today': date.today(),
            'current_version': followup_case.version,
            'followup_type': '28',
        }
    )


# ==========================================
# READ-ONLY VIEW
# ==========================================

@login_required
@require_crf_view('fu_contact_28', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTFOLLOWUP28', get_patient_id_from='usubjid')
def contact_followup_28_view(request, usubjid):
    """
    View contact follow-up Day 28 (read-only)
    
    Permission: view_contactfollowup28
    """
    logger.info(f"=== CONTACT FOLLOW-UP DAY 28 VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get follow-up with related data
    enrollment_contact, followup_case = get_contact_followup28_with_related(request,usubjid)
    
    if not followup_case:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin theo dõi Day 28.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        followup_case,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Create read-only forms
    followup_form = ContactFollowUp28Form(instance=followup_case)
    medication_formset = ContactMedicationHistory28FormSet(
        instance=followup_case,
        prefix='medication'
    )
    
    # Make everything readonly
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
        'followup_type': '28',
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_followup_28.html', context)