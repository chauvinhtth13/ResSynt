# backends/studies/study_43en/views/contact/ENR/views_enr_contact.py

"""
Contact Enrollment Views - REFACTORED with Universal Audit System
"""

import logging
from datetime import date
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_43en.models.contact import (
    SCR_CONTACT, ENR_CONTACT, ContactUnderlyingCondition, ENR_CONTACT_MedHisDrug
)

from backends.studies.study_43en.forms.contact.contact_ENR import (
    ContactMedHisDrugFormSet,
    ContactUnderlyingConditionForm,
    EnrollmentContactForm,
)

from backends.studies.study_43en.utils.audit.decorators import audit_log
from backends.studies.study_43en.utils.audit.processors import process_complex_update
from backends.studies.study_43en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def set_audit_metadata(instance, user):
    """Set audit fields"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


def get_contact_enrollment_with_related(request, usubjid):
    """
    Get contact enrollment with optimized queries (WITH SITE FILTERING)
    
    Args:
        request: HttpRequest (for site filtering)
        usubjid: Contact USUBJID
        
    Returns:
        tuple: (screening_contact, enrollment_contact or None)
        
    Raises:
        Http404: If screening not found OR user lacks site access
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    # Get site filtering params
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get screening contact with site filtering
    screening_contact = get_site_filtered_object_or_404(
        SCR_CONTACT, site_filter, filter_type, USUBJID=usubjid
    )
    
    try:
        enrollment_contact = ENR_CONTACT.objects.select_related(
            'USUBJID'
        ).prefetch_related(
            'medhisdrug_set',
            'underlying_condition'
        ).get(USUBJID=screening_contact)
        
        return screening_contact, enrollment_contact
    except ENR_CONTACT.DoesNotExist:
        return screening_contact, None


def save_contact_enrollment_and_related(request, forms_dict, screening_contact, is_create=False):
    """
    Save contact enrollment and related in transaction - NO DELETE HANDLING
    
    Args:
        request: HttpRequest
        forms_dict: Dict with 'main', 'related', 'formsets'
        screening_contact: SCR_CONTACT instance
        is_create: bool
    
    Returns:
        ENR_CONTACT instance or None
    """
    try:
        with transaction.atomic():
            # 1. Save main enrollment contact
            enrollment = forms_dict['main'].save(commit=False)
            
            if is_create:
                enrollment.USUBJID = screening_contact
            
            set_audit_metadata(enrollment, request.user)
            enrollment.save()
            
            logger.info(f"{'Created' if is_create else 'Updated'} contact enrollment: {enrollment.USUBJID.USUBJID}")
            
            # 2. Save underlying conditions
            underlying = forms_dict['related']['underlying'].save(commit=False)
            underlying.USUBJID = enrollment
            set_audit_metadata(underlying, request.user)
            underlying.save()
            
            logger.info(f"Saved contact underlying conditions")
            
            # 3. Save medications formset (NO DELETE)
            medications_formset = forms_dict['formsets']['medications']
            
            #  Save all instances (no delete handling needed)
            medications = medications_formset.save(commit=False)
            
            for med in medications:
                med.USUBJID = enrollment
                set_audit_metadata(med, request.user)
                med.save()
            
            # Save M2M relationships
            medications_formset.save_m2m()
            
            logger.info(f"Saved {len(medications)} contact medications")
            
            return enrollment
            
    except Exception as e:
        logger.error(f"Error saving contact enrollment: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu: {str(e)}')
        return None


def make_form_readonly(form):
    """Make form readonly"""
    for field in form.fields.values():
        field.disabled = True
        field.widget.attrs.update({'readonly': True, 'disabled': True})


def make_formset_readonly(formset):
    """Make formset readonly"""
    for form in formset.forms:
        make_form_readonly(form)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('enr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(model_name='ENROLLMENTCONTACT', get_patient_id_from='usubjid')
def enrollment_contact_create(request, usubjid):
    """Create new contact enrollment - NO AUDIT"""
    logger.info(f"=== CONTACT ENROLLMENT CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get screening contact
    screening_contact = get_object_or_404(SCR_CONTACT, USUBJID=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request, screening_contact, redirect_to='study_43en:screening_contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if exists
    if hasattr(screening_contact, 'enrollment_contact'):
        messages.info(request, f'Contact {usubjid} đã có thông tin đăng ký.')
        return redirect('study_43en:enrollment_contact_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        enrollment_form = EnrollmentContactForm(request.POST)
        #  WITH PREFIX
        medhisdrug_formset = ContactMedHisDrugFormSet(
            request.POST, 
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = ContactUnderlyingConditionForm(request.POST, instance=None)
        
        if all([enrollment_form.is_valid(), medhisdrug_formset.is_valid(), 
                underlying_form.is_valid()]):
            
            forms_dict = {
                'main': enrollment_form,
                'related': {'underlying': underlying_form},
                'formsets': {'medications': medhisdrug_formset}
            }
            
            enrollment = save_contact_enrollment_and_related(
                request, forms_dict, screening_contact, is_create=True
            )
            
            if enrollment:
                messages.success(
                    request,
                    f' Đã tạo thông tin đăng ký cho contact {usubjid} thành công.'
                )
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            # Log validation errors
            if enrollment_form.errors:
                logger.warning(f"Contact enrollment form errors: {enrollment_form.errors}")
            if medhisdrug_formset.errors:
                logger.warning(f"Contact medication formset errors: {medhisdrug_formset.errors}")
            if underlying_form.errors:
                logger.warning(f"Contact underlying form errors: {underlying_form.errors}")
            
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        initial_data = {'ENRDATE': screening_contact.SCREENINGFORMDATE or date.today()}
        enrollment_form = EnrollmentContactForm(initial=initial_data)
        #  WITH PREFIX
        medhisdrug_formset = ContactMedHisDrugFormSet(
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = ContactUnderlyingConditionForm(instance=None)
    
    context = {
        'form': enrollment_form,
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'screening_contact': screening_contact,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_contact.SITEID,
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_enrollment_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('enr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(model_name='ENROLLMENTCONTACT', get_patient_id_from='usubjid')
def enrollment_contact_update(request, usubjid):
    """Update contact enrollment WITH UNIVERSAL AUDIT SYSTEM"""
    logger.info(f"=== CONTACT ENROLLMENT UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get enrollment contact (WITH SITE FILTERING)
    screening_contact, enrollment_contact = get_contact_enrollment_with_related(request, usubjid)
    
    if not enrollment_contact:
        messages.warning(request, f'Contact {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:enrollment_contact_create', usubjid=usubjid)
    
    #  Site access already verified by helper function
    
    # Get or create underlying
    try:
        underlying = enrollment_contact.underlying_condition
    except ContactUnderlyingCondition.DoesNotExist:
        underlying = ContactUnderlyingCondition(USUBJID=enrollment_contact)
    
    # GET - Show current data
    if request.method == 'GET':
        enrollment_form = EnrollmentContactForm(instance=enrollment_contact)
        #  WITH PREFIX
        medhisdrug_formset = ContactMedHisDrugFormSet(
            instance=enrollment_contact,
            prefix='medhisdrug_set'
        )
        underlying_form = ContactUnderlyingConditionForm(instance=underlying)
        
        context = {
            'form': enrollment_form,
            'medhisdrug_formset': medhisdrug_formset,
            'underlying_form': underlying_form,
            'enrollment_contact': enrollment_contact,
            'screening_contact': screening_contact,
            'is_create': False,
            'is_readonly': False,
            'current_version': enrollment_contact.version,
            'selected_site_id': request.session.get('selected_site_id', 'all'),
        }
        
        return render(request, 'studies/study_43en/CRF/contact/contact_enrollment_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM
    logger.info(" Using Universal Audit System (Tier 3)")
    
    # Configure forms
    forms_config = {
        'main': {
            'class': EnrollmentContactForm,
            'instance': enrollment_contact
        },
        'related': {
            'underlying': {
                'class': ContactUnderlyingConditionForm,
                'instance': underlying
            }
        },
        'formsets': {
            'medications': {
                'class': ContactMedHisDrugFormSet,
                'instance': enrollment_contact,
                'prefix': 'medhisdrug_set',  #  WITH PREFIX
                'related_name': 'medhisdrug_set'
            }
        }
    }
    
    # Define save callback
    def save_callback(request, forms_dict):
        return save_contact_enrollment_and_related(
            request, forms_dict, screening_contact, is_create=False
        )
    
    # Use Universal Audit System
    return process_complex_update(
        request=request,
        main_instance=enrollment_contact,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/CRF/contact/contact_enrollment_form.html',
        redirect_url=reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'enrollment_contact': enrollment_contact,
            'screening_contact': screening_contact,
            'current_version': enrollment_contact.version,
            'selected_site_id': request.session.get('selected_site_id', 'all'),
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('enr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(model_name='ENROLLMENTCONTACT', get_patient_id_from='usubjid')
def enrollment_contact_view(request, usubjid):
    """View contact enrollment (read-only)"""
    logger.info(f"=== CONTACT ENROLLMENT VIEW (READ-ONLY) ===")
    
    # Get enrollment contact (WITH SITE FILTERING)
    screening_contact, enrollment_contact = get_contact_enrollment_with_related(request, usubjid)
    
    if not enrollment_contact:
        messages.error(request, f'Contact {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    #  Site access already verified by helper function
    
    # Get underlying
    try:
        underlying = enrollment_contact.underlying_condition
    except ContactUnderlyingCondition.DoesNotExist:
        underlying = None
    
    # Create readonly forms
    enrollment_form = EnrollmentContactForm(instance=enrollment_contact)
    #  WITH PREFIX
    medhisdrug_formset = ContactMedHisDrugFormSet(
        instance=enrollment_contact,
        prefix='medhisdrug_set'
    )
    underlying_form = ContactUnderlyingConditionForm(instance=underlying)
    
    make_form_readonly(enrollment_form)
    make_formset_readonly(medhisdrug_formset)
    if underlying_form:
        make_form_readonly(underlying_form)
    
    context = {
        'form': enrollment_form,
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'enrollment_contact': enrollment_contact,
        'screening_contact': screening_contact,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': request.session.get('selected_site_id', 'all'),
    }
    
    return render(request, 'studies/study_43en/CRF/contact/contact_enrollment_form.html', context)