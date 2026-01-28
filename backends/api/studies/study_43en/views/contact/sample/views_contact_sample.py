# backends/studies/study_43en/views/contact/sample/views_contact_sample.py
"""
Contact Sample Collection CRUD Views - REFACTORED with Universal Audit System
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

# Import forms
from backends.studies.study_43en.forms.contact.contact_SAM import ContactSampleCollectionForm

# Import models
from backends.studies.study_43en.models.contact import (
    SCR_CONTACT,
    ENR_CONTACT,
    SAM_CONTACT
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

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_contact_enrollment_with_samples(usubjid):
    """Get contact enrollment and related samples"""
    enrollment_contact = get_object_or_404(
        ENR_CONTACT.objects.select_related('USUBJID'),
        USUBJID__USUBJID=usubjid
    )
    
    screening_contact = enrollment_contact.USUBJID
    samples = SAM_CONTACT.objects.filter(USUBJID=enrollment_contact).order_by('SAMPLE_TYPE')
    
    return screening_contact, enrollment_contact, samples


def validate_sample_type(sample_type):
    """Validate sample type"""
    valid_types = [choice[0] for choice in SAM_CONTACT.SampleTypeChoices.choices]
    return sample_type in valid_types


def check_contact_sample_exists(enrollment_contact, sample_type):
    """Check if contact sample already exists"""
    return SAM_CONTACT.objects.filter(
        USUBJID=enrollment_contact,
        SAMPLE_TYPE=sample_type
    ).exists()


def get_single_contact_sample(enrollment_contact, sample_type):
    """Get single contact sample or None"""
    try:
        return SAM_CONTACT.objects.get(
            USUBJID=enrollment_contact,
            SAMPLE_TYPE=sample_type
        )
    except SAM_CONTACT.DoesNotExist:
        return None


# ==========================================
# LIST VIEW
# ==========================================

@login_required
@require_crf_view('sam_contact', redirect_to='study_43en:contact_list')
def contact_sample_collection_list(request, usubjid):
    """
    Display list of sample collections for a contact
    
    Permission: view_contactsamplecollection
    """
    logger.info(f"=== CONTACT SAMPLE COLLECTION LIST ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get data
    screening_contact, enrollment_contact, samples = get_contact_enrollment_with_samples(usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_contact,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Check view mode
    mode = request.GET.get('mode', 'edit')
    is_view_only = mode == 'view'
    
    # Prepare data
    sample_types = SAM_CONTACT.SampleTypeChoices.choices
    samples_by_type = {sample.SAMPLE_TYPE: sample for sample in samples}
    
    context = {
        'usubjid': usubjid,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'sample_types': sample_types,
        'samples': samples,
        'samples_by_type': samples_by_type,
        'is_view_only': is_view_only,
        'selected_site_id': screening_contact.SITEID,
    }
    
    logger.info(f" Loaded {samples.count()} contact samples")
    
    return render(request, 'studies/study_43en/contact/list/contact_sample_collection_list.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('sam_contact', redirect_to='study_43en:contact_list')
@audit_log(
    model_name='CONTACTSAMPLECOLLECTION',
    get_patient_id_from='usubjid',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def contact_sample_collection_create(request, usubjid, sample_type):
    """
    Create new contact sample collection (NO AUDIT)
    
    Permission: add_contactsamplecollection
    """
    logger.info(f"=== CONTACT SAMPLE COLLECTION CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Type: {sample_type}")
    
    # Validate sample type
    if not validate_sample_type(sample_type):
        messages.error(request, f' Sample type không hợp lệ: {sample_type}')
        return redirect('study_43en:contact_sample_collection_list', usubjid=usubjid)
    
    # Get enrollment
    screening_contact, enrollment_contact, _ = get_contact_enrollment_with_samples(usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_contact,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if already exists
    if check_contact_sample_exists(enrollment_contact, sample_type):
        logger.info(f" Contact sample exists, redirecting to update")
        messages.info(request, f'Mẫu {sample_type} của contact đã tồn tại. Chuyển sang cập nhật.')
        return redirect('study_43en:contact_sample_collection_update',
                       usubjid=usubjid, sample_type=sample_type)
    
    # POST - Handle form submission with SAMPLE_TYPE injection
    if request.method == 'POST':
        #  FIX: Add SAMPLE_TYPE to POST data before form validation
        post_data = request.POST.copy()
        post_data['SAMPLE_TYPE'] = sample_type
        
        # Create form with modified POST data
        form = ContactSampleCollectionForm(post_data, request.FILES, contact=enrollment_contact)
        
        if form.is_valid():
            try:
                logger.info(" Form valid, creating contact sample...")
                
                with transaction.atomic():
                    # Save form
                    instance = form.save(commit=False)
                    
                    # Apply pre-save callback
                    instance.USUBJID = enrollment_contact
                    instance.SAMPLE_TYPE = sample_type
                    
                    # Save instance
                    instance.save()
                    
                    logger.info(f" Contact sample created successfully: {instance}")
                    messages.success(request, ' Tạo mẫu contact thành công!')
                    
                    return redirect('study_43en:contact_sample_collection_list', usubjid=usubjid)
                    
            except Exception as e:
                logger.error(f" Error creating contact sample: {e}", exc_info=True)
                messages.error(request, f' Lỗi khi tạo mẫu: {str(e)}')
        else:
            # Form validation failed - show errors
            logger.error(f" Form validation failed: {form.errors}")
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi!')
        
        # Re-render form with errors
        context = {
            'form': form,
            'sample': None,
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'sample_type_display': dict(SAM_CONTACT.SampleTypeChoices.choices).get(sample_type, sample_type),
            'is_create': True,
            'is_readonly': False,
            'selected_site_id': screening_contact.SITEID,
        }
        return render(request, 'studies/study_43en/contact/form/contact_sample_collection_form.html', context)
    
    # GET - Show blank form
    logger.info(" Showing blank form for contact sample")
    form = ContactSampleCollectionForm(contact=enrollment_contact, initial={'SAMPLE_TYPE': sample_type})
    
    context = {
        'form': form,
        'sample': None,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'sample_type_display': dict(SAM_CONTACT.SampleTypeChoices.choices).get(sample_type, sample_type),
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_contact.SITEID,
    }
    
    return render(request, 'studies/study_43en/contact/form/contact_sample_collection_form.html', context)


# ==========================================
# UPDATE VIEW WITH AUDIT
# ==========================================

@login_required
@require_crf_change('sam_contact', redirect_to='study_43en:contact_list')
@audit_log(
    model_name='CONTACTSAMPLECOLLECTION',
    get_patient_id_from='usubjid',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def contact_sample_collection_update(request, usubjid, sample_type):
    """
    Update contact sample collection WITH UNIVERSAL AUDIT SYSTEM (Tier 1)
    
    Permission: change_contactsamplecollection
    """
    logger.info(f"=== CONTACT SAMPLE COLLECTION UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Type: {sample_type}, Method: {request.method}")
    
    # Validate sample type
    if not validate_sample_type(sample_type):
        messages.error(request, f' Sample type không hợp lệ: {sample_type}')
        return redirect('study_43en:contact_sample_collection_list', usubjid=usubjid)
    
    # Get enrollment and sample
    screening_contact, enrollment_contact, _ = get_contact_enrollment_with_samples(usubjid)
    sample = get_single_contact_sample(enrollment_contact, sample_type)
    
    if not sample:
        messages.error(request, f' Không tìm thấy mẫu contact {sample_type}')
        return redirect('study_43en:contact_sample_collection_list', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_contact,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # GET - Show current data
    if request.method == 'GET':
        form = ContactSampleCollectionForm(instance=sample, contact=enrollment_contact)
        
        context = {
            'form': form,
            'sample': sample,
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'sample_type_display': dict(SAM_CONTACT.SampleTypeChoices.choices).get(sample_type, sample_type),
            'is_create': False,
            'is_readonly': False,
            'selected_site_id': screening_contact.SITEID,
            'current_version': sample.version,
        }
        
        return render(request, 'studies/study_43en/contact/form/contact_sample_collection_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 1)
    logger.info(" Using Universal Audit System (Tier 1) for contact sample")
    
    return process_crf_update(
        request=request,
        instance=sample,
        form_class=ContactSampleCollectionForm,
        template_name='studies/study_43en/contact/form/contact_sample_collection_form.html',
        redirect_url=reverse('study_43en:contact_sample_collection_list', kwargs={'usubjid': usubjid}),
        extra_context={
            'sample': sample,
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'sample_type_display': dict(SAM_CONTACT.SampleTypeChoices.choices).get(sample_type, sample_type),
            'selected_site_id': screening_contact.SITEID,
            'current_version': sample.version,
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('sam_contact', redirect_to='study_43en:contact_list')
@audit_log(
    model_name='CONTACTSAMPLECOLLECTION',
    get_patient_id_from='usubjid',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def contact_sample_collection_view(request, usubjid, sample_type):
    """
    View contact sample in read-only mode
    
    Permission: view_contactsamplecollection
    """
    logger.info(f"=== CONTACT SAMPLE COLLECTION VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Type: {sample_type}")
    
    # Validate sample type
    if not validate_sample_type(sample_type):
        messages.error(request, f' Sample type không hợp lệ: {sample_type}')
        return redirect('study_43en:contact_sample_collection_list', usubjid=usubjid)
    
    # Get data
    screening_contact, enrollment_contact, _ = get_contact_enrollment_with_samples(usubjid)
    sample = get_single_contact_sample(enrollment_contact, sample_type)
    
    if not sample:
        messages.error(request, f' Không tìm thấy mẫu contact {sample_type}')
        return redirect('study_43en:contact_sample_collection_list', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_contact,
        redirect_to='study_43en:contact_list'
    )
    if site_check is not True:
        return site_check
    
    # Create read-only form
    form = ContactSampleCollectionForm(instance=sample, contact=enrollment_contact)
    
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    context = {
        'form': form,
        'sample': sample,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'sample_type_display': dict(SAM_CONTACT.SampleTypeChoices.choices).get(sample_type, sample_type),
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': screening_contact.SITEID,
    }
    
    return render(request, 'studies/study_43en/contact/form/contact_sample_collection_form.html', context)
