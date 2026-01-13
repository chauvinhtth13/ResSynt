# backends/studies/study_43en/views/patient/ENR/views_enr_case_updated.py

"""
UPDATED Enrollment Case Views - WITH PERSONAL DATA SEPARATION
==============================================================

Key Changes:
- Now manages TWO models: ENR_CASE + PERSONAL_DATA
- Uses TWO forms: EnrollmentCaseForm + PersonalDataForm
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

from backends.studies.study_43en.models.patient import (
    SCR_CASE, ENR_CASE, UnderlyingCondition, ENR_CASE_MedHisDrug, PERSONAL_DATA
)   
from backends.studies.study_43en.models import AuditLog, AuditLogDetail
from backends.studies.study_43en.forms.patient.ENR import (
    MedHisDrugFormSet,
    UnderlyingConditionForm,
    EnrollmentCaseForm,  # Updated version without PII fields,
)
from backends.studies.study_43en.forms.patient.PER_DATA import PersonalDataForm

from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import process_complex_update
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
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


def get_enrollment_with_related(request, usubjid):
    """
    Get enrollment with optimized queries - WITH SITE FILTERING
    NOW includes personal_data
    """
    site_filter, filter_type = get_site_filter_params(request)
    
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    
    site_check = check_instance_site_access(request, screening_case)
    if site_check is not True:
        return None, site_check
    
    try:
        enrollment_case = ENR_CASE.objects.select_related(
            'USUBJID',
            'personal_data' 
        ).prefetch_related(
            'medhisdrug_set',
            'Underlying_Condition'
        ).get(USUBJID=screening_case)
        
        return screening_case, enrollment_case
    except ENR_CASE.DoesNotExist:
        return screening_case, None


def save_enrollment_and_related(request, forms_dict, screening_case, is_create=False):
    """
    Save enrollment, personal data, and related models in transaction
    
     UPDATED: Now also saves PERSONAL_DATA
    """
    try:
        with transaction.atomic(using='db_study_43en'):
            # 1. Save main enrollment
            enrollment = forms_dict['main'].save(commit=False)
            
            if is_create:
                enrollment.USUBJID = screening_case
            
            set_audit_metadata(enrollment, request.user)
            enrollment.save()
            
            logger.info(f"{'Created' if is_create else 'Updated'} enrollment: {enrollment.USUBJID.USUBJID}")
            
            #  2. Save personal data (NEW)
            personal_form = forms_dict.get('personal')
            if not personal_form:
                logger.error("PersonalDataForm missing in forms_dict. Check forms_config structure.")
                messages.error(request, "Không tìm thấy form thông tin cá nhân. Vui lòng kiểm tra lại forms_config.")
                return None
            
            # DEBUG: Log form data
            logger.info(f"🔍 Personal form has_changed: {personal_form.has_changed()}")
            logger.info(f"🔍 Personal form cleaned_data keys: {list(personal_form.cleaned_data.keys())}")
            logger.info(f"🔍 FULLNAME: {personal_form.cleaned_data.get('FULLNAME')}")
            logger.info(f"🔍 PHONE: {personal_form.cleaned_data.get('PHONE')}")
            logger.info(f"🔍 PRIMARY_ADDRESS: {personal_form.cleaned_data.get('PRIMARY_ADDRESS')}")
            
            personal_data = personal_form.save(commit=False)
            personal_data.USUBJID = enrollment  # Link to enrollment (OneToOne relationship)
            set_audit_metadata(personal_data, request.user)
            
            # DEBUG: Log before save
            logger.info(f"🔍 About to save personal_data with USUBJID: {personal_data.USUBJID}")
            logger.info(f"🔍 Personal data has PK: {personal_data.pk}")
            
            personal_data.save()
            
            # DEBUG: Log after save
            logger.info(f"✅ Saved personal data - PK: {personal_data.pk}, FULLNAME: {personal_data.FULLNAME}")
            
            logger.info(f"Saved personal data for {enrollment.USUBJID.USUBJID}")
            
            # 3. Save underlying conditions
            underlying = forms_dict['related']['underlying'].save(commit=False)
            underlying.USUBJID = enrollment
            set_audit_metadata(underlying, request.user)
            underlying.save()
            
            logger.info(f"Saved underlying conditions")
            
            # 4. Save medications formset
            medications_formset = forms_dict['formsets']['medications']
            medications = medications_formset.save(commit=False)
            
            for med in medications:
                med.USUBJID = enrollment
                set_audit_metadata(med, request.user)
                med.save()
            
            medications_formset.save_m2m()
            
            logger.info(f"Saved {len(medications)} medications")
            
            return enrollment
            
    except Exception as e:
        logger.error(f"Error saving enrollment: {e}", exc_info=True)
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
@require_crf_add('enr_case', redirect_to='study_43en:screening_case_list')
@audit_log(
    model_name='ENROLLMENTCASE',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def enrollment_case_create(request, usubjid):
    """
    Create new enrollment WITH personal data
     UPDATED: Now handles PersonalDataForm
    """
    logger.info(f"=== ENROLLMENT CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    site_filter, filter_type = get_site_filter_params(request)
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    
    siteid = screening_case.SITEID
    
    site_check = check_instance_site_access(
        request, screening_case, redirect_to='study_43en:screening_case_list'
    )
    if site_check is not True:
        return site_check
    
    # Check if exists
    if hasattr(screening_case, 'enrollment_case'):
        messages.info(request, f'Bệnh nhân {usubjid} đã có thông tin đăng ký.')
        return redirect('study_43en:enrollment_case_update', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        enrollment_form = EnrollmentCaseForm(request.POST, siteid=siteid)
        personal_form = PersonalDataForm(request.POST) 
        medhisdrug_formset = MedHisDrugFormSet(
            request.POST, 
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = UnderlyingConditionForm(request.POST, instance=None)
        
        if all([
            enrollment_form.is_valid(),
            personal_form.is_valid(), 
            medhisdrug_formset.is_valid(), 
            underlying_form.is_valid()
        ]):
            
            forms_dict = {
                'main': enrollment_form,
                'personal': personal_form,  
                'related': {'underlying': underlying_form},
                'formsets': {'medications': medhisdrug_formset}
            }
            
            enrollment = save_enrollment_and_related(
                request, forms_dict, screening_case, is_create=True
            )
            
            if enrollment:
                messages.success(
                    request,
                    f'✅ Đã tạo thông tin đăng ký cho bệnh nhân {usubjid} thành công.'
                )
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            # Log validation errors
            if enrollment_form.errors:
                logger.warning(f"Enrollment form errors: {enrollment_form.errors}")
            if personal_form.errors: 
                logger.warning(f"Personal data form errors: {personal_form.errors}")
            if medhisdrug_formset.errors:
                logger.warning(f"Medication formset errors: {medhisdrug_formset.errors}")
            if underlying_form.errors:
                logger.warning(f"Underlying form errors: {underlying_form.errors}")
            
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        initial_data = {'ENRDATE': screening_case.SCREENINGFORMDATE or date.today()}
        enrollment_form = EnrollmentCaseForm(initial=initial_data, siteid=siteid)
        personal_form = PersonalDataForm()  
        medhisdrug_formset = MedHisDrugFormSet(
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = UnderlyingConditionForm(instance=None)
    
    context = {
        'form': enrollment_form,
        'personal_form': personal_form,  
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'screening_case': screening_case,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': siteid,
    }
    
    return render(request, 'studies/study_43en/patient/form/enrollment_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('enr_case', redirect_to='study_43en:screening_case_list')
@audit_log(
    model_name='ENROLLMENTCASE',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def enrollment_case_update(request, usubjid):
    """
    Update enrollment WITH UNIVERSAL AUDIT SYSTEM
     UPDATED: Now handles PersonalDataForm
    """
    logger.info(f"=== ENROLLMENT UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    result = get_enrollment_with_related(request, usubjid)
    
    if result[0] is None:
        return result[1]
    
    screening_case, enrollment_case = result
    
    if not enrollment_case:
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:enrollment_case_create', usubjid=usubjid)
    
    siteid = enrollment_case.SITEID
    
    site_check = check_instance_site_access(
        request, enrollment_case, redirect_to='study_43en:screening_case_list'
    )
    if site_check is not True:
        return site_check
    
    # Get or create related records
    try:
        underlying = enrollment_case.Underlying_Condition
    except UnderlyingCondition.DoesNotExist:
        underlying = UnderlyingCondition(USUBJID=enrollment_case)
    
    #  Get or create personal data
    try:
        personal_data = enrollment_case.personal_data
    except PERSONAL_DATA.DoesNotExist:
        personal_data = PERSONAL_DATA(USUBJID=enrollment_case)
    
    # GET - Show current data
    if request.method == 'GET':
        enrollment_form = EnrollmentCaseForm(instance=enrollment_case, siteid=siteid)
        personal_form = PersonalDataForm(instance=personal_data)  
        medhisdrug_formset = MedHisDrugFormSet(
            instance=enrollment_case,
            prefix='medhisdrug_set'
        )
        underlying_form = UnderlyingConditionForm(instance=underlying)
        
        context = {
            'form': enrollment_form,
            'personal_form': personal_form,  
            'medhisdrug_formset': medhisdrug_formset,
            'underlying_form': underlying_form,
            'enrollment_case': enrollment_case,
            'screening_case': screening_case,
            'is_create': False,
            'is_readonly': False,
            'current_version': enrollment_case.version,
            'selected_site_id': siteid,
        }
        
        return render(request, 'studies/study_43en/patient/form/enrollment_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (UPDATED)
    logger.info(" Using Universal Audit System (Tier 3)")
    
    forms_config = {
        'main': {
            'class': EnrollmentCaseForm,
            'instance': enrollment_case,
            'kwargs': {'siteid': siteid}
        },
        'personal': {  
            'class': PersonalDataForm,
            'instance': personal_data
        },
        'related': {
            'underlying': {
                'class': UnderlyingConditionForm,
                'instance': underlying
            }
        },
        'formsets': {
            'medications': {
                'class': MedHisDrugFormSet,
                'instance': enrollment_case,
                'prefix': 'medhisdrug_set',
                'related_name': 'medhisdrug_set'
            }
        }
    }
    
    def save_callback(request, forms_dict):
        return save_enrollment_and_related(
            request, forms_dict, screening_case, is_create=False
        )
    
    return process_complex_update(
        request=request,
        main_instance=enrollment_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/patient/form/enrollment_form.html',
        redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'enrollment_case': enrollment_case,
            'screening_case': screening_case,
            'current_version': enrollment_case.version,
            'selected_site_id': siteid,
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('enr_case', redirect_to='study_43en:screening_case_list')
@audit_log(
    model_name='ENROLLMENTCASE',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def enrollment_case_view(request, usubjid):
    """
    View enrollment (read-only)
     UPDATED: Now includes PersonalDataForm
    """
    logger.info(f"=== ENROLLMENT VIEW (READ-ONLY) ===")
    
    result = get_enrollment_with_related(request, usubjid)
    
    if result[0] is None:
        return result[1]
    
    screening_case, enrollment_case = result
    
    if not enrollment_case:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    site_check = check_instance_site_access(
        request, enrollment_case, redirect_to='study_43en:screening_case_list'
    )
    if site_check is not True:
        return site_check
    
    # Get underlying
    try:
        underlying = enrollment_case.Underlying_Condition
    except UnderlyingCondition.DoesNotExist:
        underlying = None
    
    #  Get personal data
    try:
        personal_data = enrollment_case.personal_data
    except PERSONAL_DATA.DoesNotExist:
        personal_data = None
    
    # Create readonly forms
    siteid = enrollment_case.SITEID
    enrollment_form = EnrollmentCaseForm(instance=enrollment_case, siteid=siteid)
    personal_form = PersonalDataForm(instance=personal_data) if personal_data else None  #  NEW
    medhisdrug_formset = MedHisDrugFormSet(
        instance=enrollment_case,
        prefix='medhisdrug_set'
    )
    underlying_form = UnderlyingConditionForm(instance=underlying)
    
    make_form_readonly(enrollment_form)
    if personal_form:
        make_form_readonly(personal_form)  
    make_formset_readonly(medhisdrug_formset)
    if underlying_form:
        make_form_readonly(underlying_form)
    
    context = {
        'form': enrollment_form,
        'personal_form': personal_form,  
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'enrollment_case': enrollment_case,
        'screening_case': screening_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': siteid,
    }
    
    return render(request, 'studies/study_43en/patient/form/enrollment_form.html', context)
