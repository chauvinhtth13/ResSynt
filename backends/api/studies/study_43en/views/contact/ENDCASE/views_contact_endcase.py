# backends/studies/study_43en/views/contactendcase/views_contactendcase.py
"""
Contact End Case CRF CRUD Views - REFACTORED with Universal Audit System
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import forms
from backends.studies.study_43en.forms.contact.contact_ENDCASE import ContactEndCaseCRFForm

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

# Import helpers
from .helpers import (
    get_contact_endcase_with_related,
    make_form_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('contactendcasecrf', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTENDCASECRF', get_patient_id_from='usubjid')
def contactendcase_create(request, usubjid):
    """
    Create new contact end case CRF (NO AUDIT)
    
    Permission: add_contactendcasecrf
    """
    logger.info(f"=== CONTACT END CASE CRF CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and check if end case exists
    screening_contact, enrollment_contact, endcase = get_contact_endcase_with_related(request,usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_contact,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if end case already exists
    if endcase:
        messages.info(request, f'Contact {usubjid} đã có phiếu kết thúc nghiên cứu.')
        return redirect('study_43en:contactendcase_update', usubjid=usubjid)
    
    # Pre-save callback
    def pre_save(instance):
        instance.USUBJID = enrollment_contact
    
    # POST - Use universal create processor
    if request.method == 'POST':
        return process_crf_create(
            request=request,
            form_class=ContactEndCaseCRFForm,
            template_name='studies/study_43en/CRF/contact/contact_endcase_form.html',
            redirect_url=reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid}),
            pre_save_callback=pre_save,
            extra_context={
                'endcase': None,
                'screening_contact': screening_contact,
                'enrollment_contact': enrollment_contact,
                'selected_site_id': screening_contact.SITEID,
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
    
    form = ContactEndCaseCRFForm(
        initial=initial_data,
        contact=enrollment_contact
    )
    
    context = {
        'form': form,
        'endcase': None,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_contact.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_endcase_form.html', context)


# ==========================================
# UPDATE VIEW WITH AUDIT
# ==========================================

@login_required
@require_crf_change('contactendcasecrf', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTENDCASECRF', get_patient_id_from='usubjid')
def contactendcase_update(request, usubjid):
    """
    Update contact end case CRF WITH UNIVERSAL AUDIT SYSTEM (Tier 1)
    
    Permission: change_contactendcasecrf
    """
    logger.info(f"=== CONTACT END CASE CRF UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get end case with related data
    screening_contact, enrollment_contact, endcase = get_contact_endcase_with_related(request,usubjid)
    
    if not endcase:
        messages.warning(request, f'Contact {usubjid} chưa có phiếu kết thúc nghiên cứu.')
        return redirect('study_43en:contactendcase_create', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        endcase,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        form = ContactEndCaseCRFForm(
            instance=endcase,
            contact=enrollment_contact
        )
        
        context = {
            'form': form,
            'endcase': endcase,
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': screening_contact.SITEID,
            'today': date.today(),
            'current_version': endcase.version,
        }
        
        return render(request, 'studies/study_43en/CRF/contact/contact_endcase_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 1)
    logger.info(" Using Universal Audit System (Tier 1)")
    
    #  Form tự động detect contact từ instance
    return process_crf_update(
        request=request,
        instance=endcase,
        form_class=ContactEndCaseCRFForm,
        template_name='studies/study_43en/CRF/contact/contact_endcase_form.html',
        redirect_url=reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'endcase': endcase,
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'selected_site_id': screening_contact.SITEID,
            'current_version': endcase.version,
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('contactendcasecrf', redirect_to='study_43en:contact_list')
@audit_log(model_name='CONTACTENDCASECRF', get_patient_id_from='usubjid')
def contactendcase_view(request, usubjid):
    """
    View contact end case CRF in read-only mode
    
    Permission: view_contactendcasecrf
    """
    logger.info(f"=== CONTACT END CASE CRF VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get end case with related data
    screening_contact, enrollment_contact, endcase = get_contact_endcase_with_related(request,usubjid)
    
    if not endcase:
        messages.error(request, f'Contact {usubjid} chưa có phiếu kết thúc nghiên cứu.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        endcase,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Create read-only form
    form = ContactEndCaseCRFForm(
        instance=endcase,
        contact=enrollment_contact
    )
    
    # Make all fields readonly
    make_form_readonly(form)
    
    context = {
        'form': form,
        'endcase': endcase,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': screening_contact.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_endcase_form.html', context)