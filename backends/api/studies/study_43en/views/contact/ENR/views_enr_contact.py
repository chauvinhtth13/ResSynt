# backends/studies/study_43en/views/contact/ENR/views_enr_contact_updated.py

"""
UPDATED Contact Enrollment Views - WITH PERSONAL DATA SEPARATION
=================================================================

Key Changes:
- Now manages TWO models: ENR_CONTACT + PERSONAL_CONTACT_DATA
- Uses TWO forms: EnrollmentContactForm + PersonalContactDataForm
- Saves both in transaction
- Universal Audit System tracks both changes
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
from backends.studies.study_43en.models.contact.PER_CONTACT_DATA import PERSONAL_CONTACT_DATA
from backends.studies.study_43en.models import AuditLog, AuditLogDetail

from backends.studies.study_43en.forms.contact.contact_ENR import (
    ContactMedHisDrugFormSet,
    ContactUnderlyingConditionForm,
    EnrollmentContactForm,  # Updated version without PII fields
)
from backends.studies.study_43en.forms.contact.contact_PER_DATA import PersonalContactDataForm

from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import process_complex_update
from backends.audit_logs.utils.permission_decorators import (
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
    Get contact enrollment with optimized queries - WITH SITE FILTERING
    NOW includes personal_data
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    site_filter, filter_type = get_site_filter_params(request)
    
    screening_contact = get_site_filtered_object_or_404(
        SCR_CONTACT, site_filter, filter_type, USUBJID=usubjid
    )
    
    try:
        enrollment_contact = ENR_CONTACT.objects.select_related(
            'USUBJID',
            'personal_data'  # ✨ NEW: Include personal data
        ).prefetch_related(
            'medhisdrug_set',
            'underlying_condition'
        ).get(USUBJID=screening_contact)
        
        return screening_contact, enrollment_contact
    except ENR_CONTACT.DoesNotExist:
        return screening_contact, None


def save_contact_enrollment_and_related(request, forms_dict, screening_contact, is_create=False):
    """
    Save contact enrollment, personal data, and related models in transaction
    
    ✨ UPDATED: Now also saves PERSONAL_CONTACT_DATA
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
            
            # ✨ 2. Save personal data (NEW)
            personal_data = forms_dict['personal'].save(commit=False)
            personal_data.USUBJID = enrollment
            set_audit_metadata(personal_data, request.user)
            personal_data.save()
            
            logger.info(f"Saved contact personal data")
            
            # 3. Save underlying conditions
            underlying = forms_dict['related']['underlying'].save(commit=False)
            underlying.USUBJID = enrollment
            set_audit_metadata(underlying, request.user)
            underlying.save()
            
            logger.info(f"Saved contact underlying conditions")
            
            # 4. Save medications formset
            medications_formset = forms_dict['formsets']['medications']
            medications = medications_formset.save(commit=False)
            
            for med in medications:
                med.USUBJID = enrollment
                set_audit_metadata(med, request.user)
                med.save()
            
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
@audit_log(
    model_name='ENROLLMENTCONTACT',
    get_patient_id_from='usubjid',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def enrollment_contact_create(request, usubjid):
    """
    Create new contact enrollment WITH personal data
    ✨ UPDATED: Now handles PersonalContactDataForm
    """
    logger.info(f"=== CONTACT ENROLLMENT CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    screening_contact = get_object_or_404(SCR_CONTACT, USUBJID=usubjid)
    
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
        personal_form = PersonalContactDataForm(request.POST)  # ✨ NEW
        medhisdrug_formset = ContactMedHisDrugFormSet(
            request.POST, 
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = ContactUnderlyingConditionForm(request.POST, instance=None)
        
        if all([
            enrollment_form.is_valid(),
            personal_form.is_valid(),  # ✨ NEW
            medhisdrug_formset.is_valid(), 
            underlying_form.is_valid()
        ]):
            
            forms_dict = {
                'main': enrollment_form,
                'personal': personal_form,  # ✨ NEW
                'related': {'underlying': underlying_form},
                'formsets': {'medications': medhisdrug_formset}
            }
            
            enrollment = save_contact_enrollment_and_related(
                request, forms_dict, screening_contact, is_create=True
            )
            
            if enrollment:
                messages.success(
                    request,
                    f'✅ Đã tạo thông tin đăng ký cho contact {usubjid} thành công.'
                )
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            # Log validation errors
            if enrollment_form.errors:
                logger.warning(f"Contact enrollment form errors: {enrollment_form.errors}")
            if personal_form.errors:  # ✨ NEW
                logger.warning(f"Contact personal data form errors: {personal_form.errors}")
            if medhisdrug_formset.errors:
                logger.warning(f"Contact medication formset errors: {medhisdrug_formset.errors}")
            if underlying_form.errors:
                logger.warning(f"Contact underlying form errors: {underlying_form.errors}")
            
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        initial_data = {'ENRDATE': screening_contact.SCREENINGFORMDATE or date.today()}
        enrollment_form = EnrollmentContactForm(initial=initial_data)
        personal_form = PersonalContactDataForm()  # ✨ NEW
        medhisdrug_formset = ContactMedHisDrugFormSet(
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = ContactUnderlyingConditionForm(instance=None)
    
    context = {
        'form': enrollment_form,
        'personal_form': personal_form,  # ✨ NEW
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'screening_contact': screening_contact,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_contact.SITEID,
    }
    
    return render(request, 'studies/study_43en/contact/form/contact_enrollment_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('enr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(
    model_name='ENROLLMENTCONTACT',
    get_patient_id_from='usubjid',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def enrollment_contact_update(request, usubjid):
    """
    Update contact enrollment WITH UNIVERSAL AUDIT SYSTEM
    ✨ UPDATED: Now handles PersonalContactDataForm
    """
    logger.info(f"=== CONTACT ENROLLMENT UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get enrollment contact (WITH SITE FILTERING)
    screening_contact, enrollment_contact = get_contact_enrollment_with_related(request, usubjid)
    
    if not enrollment_contact:
        messages.warning(request, f'Contact {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:enrollment_contact_create', usubjid=usubjid)
    
    # Get or create related records
    try:
        underlying = enrollment_contact.underlying_condition
    except ContactUnderlyingCondition.DoesNotExist:
        underlying = ContactUnderlyingCondition(USUBJID=enrollment_contact)
    
    # ✨ Get or create personal data
    try:
        personal_data = enrollment_contact.personal_data
    except PERSONAL_CONTACT_DATA.DoesNotExist:
        personal_data = PERSONAL_CONTACT_DATA(USUBJID=enrollment_contact)
    
    # GET - Show current data
    if request.method == 'GET':
        enrollment_form = EnrollmentContactForm(instance=enrollment_contact)
        personal_form = PersonalContactDataForm(instance=personal_data)  # ✨ NEW
        medhisdrug_formset = ContactMedHisDrugFormSet(
            instance=enrollment_contact,
            prefix='medhisdrug_set'
        )
        underlying_form = ContactUnderlyingConditionForm(instance=underlying)
        
        context = {
            'form': enrollment_form,
            'personal_form': personal_form,  # ✨ NEW
            'medhisdrug_formset': medhisdrug_formset,
            'underlying_form': underlying_form,
            'enrollment_contact': enrollment_contact,
            'screening_contact': screening_contact,
            'is_create': False,
            'is_readonly': False,
            'current_version': enrollment_contact.version,
            'selected_site_id': request.session.get('selected_site_id', 'all'),
        }
        
        return render(request, 'studies/study_43en/contact/form/contact_enrollment_form.html', context)
    
    # ✨ POST - USE UNIVERSAL AUDIT SYSTEM (UPDATED)
    logger.info("✨ Using Universal Audit System (Tier 3)")
    
    forms_config = {
        'main': {
            'class': EnrollmentContactForm,
            'instance': enrollment_contact
        },
        'personal': {  # ✨ NEW
            'class': PersonalContactDataForm,
            'instance': personal_data
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
                'prefix': 'medhisdrug_set',
                'related_name': 'medhisdrug_set'
            }
        }
    }
    
    def save_callback(request, forms_dict):
        return save_contact_enrollment_and_related(
            request, forms_dict, screening_contact, is_create=False
        )
    
    return process_complex_update(
        request=request,
        main_instance=enrollment_contact,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/contact/form/contact_enrollment_form.html',
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
@audit_log(
    model_name='ENROLLMENTCONTACT',
    get_patient_id_from='usubjid',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def enrollment_contact_view(request, usubjid):
    """
    View contact enrollment (read-only)
    ✨ UPDATED: Now includes PersonalContactDataForm
    """
    logger.info(f"=== CONTACT ENROLLMENT VIEW (READ-ONLY) ===")
    
    # Get enrollment contact (WITH SITE FILTERING)
    screening_contact, enrollment_contact = get_contact_enrollment_with_related(request, usubjid)
    
    if not enrollment_contact:
        messages.error(request, f'Contact {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    # Get underlying
    try:
        underlying = enrollment_contact.underlying_condition
    except ContactUnderlyingCondition.DoesNotExist:
        underlying = None
    
    # ✨ Get personal data
    try:
        personal_data = enrollment_contact.personal_data
    except PERSONAL_CONTACT_DATA.DoesNotExist:
        personal_data = None
    
    # Create readonly forms
    enrollment_form = EnrollmentContactForm(instance=enrollment_contact)
    personal_form = PersonalContactDataForm(instance=personal_data) if personal_data else None  # ✨ NEW
    medhisdrug_formset = ContactMedHisDrugFormSet(
        instance=enrollment_contact,
        prefix='medhisdrug_set'
    )
    underlying_form = ContactUnderlyingConditionForm(instance=underlying)
    
    make_form_readonly(enrollment_form)
    if personal_form:
        make_form_readonly(personal_form)  # ✨ NEW
    make_formset_readonly(medhisdrug_formset)
    if underlying_form:
        make_form_readonly(underlying_form)
    
    context = {
        'form': enrollment_form,
        'personal_form': personal_form,  # ✨ NEW
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'enrollment_contact': enrollment_contact,
        'screening_contact': screening_contact,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': request.session.get('selected_site_id', 'all'),
    }
    
    return render(request, 'studies/study_43en/contact/form/contact_enrollment_form.html', context)
