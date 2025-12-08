# backends/studies/study_43en/views/patient/ENR/views_enr_case.py

"""
Enrollment Case Views - REFACTORED with Universal Audit System
"""

import logging
from datetime import date
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_43en.models.patient import (
    SCR_CASE, ENR_CASE, UnderlyingCondition, ENR_CASE_MedHisDrug
)

from backends.studies.study_43en.forms.patient.ENR import (
    MedHisDrugFormSet,
    UnderlyingConditionForm,
    EnrollmentCaseForm,
)

from backends.studies.study_43en.utils.audit.decorators import audit_log
from backends.studies.study_43en.utils.audit.processors import process_complex_update
from backends.studies.study_43en.utils.permission_decorators import (
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
    
    Args:
        request: HttpRequest
        usubjid: Patient USUBJID
    
    Returns:
        tuple: (screening_case, enrollment_case) or (None, redirect_response) if no access
    """
    # Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get screening with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    
    # Check site access
    site_check = check_instance_site_access(request, screening_case)
    if site_check is not True:
        return None, site_check
    
    try:
        enrollment_case = ENR_CASE.objects.select_related(
            'USUBJID'
        ).prefetch_related(
            'medhisdrug_set',
            'Underlying_Condition'
        ).get(USUBJID=screening_case)
        
        return screening_case, enrollment_case
    except ENR_CASE.DoesNotExist:
        return screening_case, None


def save_enrollment_and_related(request, forms_dict, screening_case, is_create=False):
    """
    Save enrollment and related in transaction - NO DELETE HANDLING
    
    Args:
        request: HttpRequest
        forms_dict: Dict with 'main', 'related', 'formsets'
        screening_case: SCR_CASE instance
        is_create: bool
    
    Returns:
        ENR_CASE instance or None
    """
    try:
        with transaction.atomic():
            # 1. Save main enrollment
            enrollment = forms_dict['main'].save(commit=False)
            
            if is_create:
                enrollment.USUBJID = screening_case
            
            set_audit_metadata(enrollment, request.user)
            enrollment.save()
            
            logger.info(f"{'Created' if is_create else 'Updated'} enrollment: {enrollment.USUBJID.USUBJID}")
            
            # 2. Save underlying conditions
            underlying = forms_dict['related']['underlying'].save(commit=False)
            underlying.USUBJID = enrollment
            set_audit_metadata(underlying, request.user)
            underlying.save()
            
            logger.info(f"Saved underlying conditions")
            
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
@audit_log(model_name='ENROLLMENTCASE', get_patient_id_from='usubjid')
def enrollment_case_create(request, usubjid):
    """Create new enrollment - WITH SITE FILTERING"""
    logger.info(f"=== ENROLLMENT CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    #  Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    #  Get screening with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    
    siteid = screening_case.SITEID  # Get SITEID
    
    #  Check site access
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
        enrollment_form = EnrollmentCaseForm(
            request.POST,
            siteid=siteid  # Pass SITEID
        )
        #  WITH PREFIX
        medhisdrug_formset = MedHisDrugFormSet(
            request.POST, 
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = UnderlyingConditionForm(request.POST, instance=None)
        
        if all([enrollment_form.is_valid(), medhisdrug_formset.is_valid(), 
                underlying_form.is_valid()]):
            
            forms_dict = {
                'main': enrollment_form,
                'related': {'underlying': underlying_form},
                'formsets': {'medications': medhisdrug_formset}
            }
            
            enrollment = save_enrollment_and_related(
                request, forms_dict, screening_case, is_create=True
            )
            
            if enrollment:
                messages.success(
                    request,
                    f' Đã tạo thông tin đăng ký cho bệnh nhân {usubjid} thành công.'
                )
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            # Log validation errors
            if enrollment_form.errors:
                logger.warning(f"Enrollment form errors: {enrollment_form.errors}")
            if medhisdrug_formset.errors:
                logger.warning(f"Medication formset errors: {medhisdrug_formset.errors}")
            if underlying_form.errors:
                logger.warning(f"Underlying form errors: {underlying_form.errors}")
            
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        initial_data = {'ENRDATE': screening_case.SCREENINGFORMDATE or date.today()}
        enrollment_form = EnrollmentCaseForm(
            initial=initial_data,
            siteid=siteid  # Pass SITEID
        )
        #  WITH PREFIX
        medhisdrug_formset = MedHisDrugFormSet(
            instance=None,
            prefix='medhisdrug_set'
        )
        underlying_form = UnderlyingConditionForm(instance=None)
    
    context = {
        'form': enrollment_form,
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'screening_case': screening_case,
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': siteid,  # Add to context
    }
    
    return render(request, 'studies/study_43en/CRF/patient/enrollment_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT)
# ==========================================

@login_required
@require_crf_change('enr_case', redirect_to='study_43en:screening_case_list')
@audit_log(model_name='ENROLLMENTCASE', get_patient_id_from='usubjid')
def enrollment_case_update(request, usubjid):
    """Update enrollment WITH UNIVERSAL AUDIT SYSTEM - WITH SITE FILTERING"""
    logger.info(f"=== ENROLLMENT UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    #  Get enrollment WITH SITE FILTERING
    result = get_enrollment_with_related(request, usubjid)
    
    # Check if we got redirect response (no access)
    if result[0] is None:
        return result[1]  # Return redirect response
    
    screening_case, enrollment_case = result
    
    if not enrollment_case:
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:enrollment_case_create', usubjid=usubjid)
    
    siteid = enrollment_case.SITEID  # Get SITEID
    
    #  Double-check site access on enrollment
    site_check = check_instance_site_access(
        request, enrollment_case, redirect_to='study_43en:screening_case_list'
    )
    if site_check is not True:
        return site_check
    
    # Get or create underlying
    try:
        underlying = enrollment_case.Underlying_Condition
    except UnderlyingCondition.DoesNotExist:
        underlying = UnderlyingCondition(USUBJID=enrollment_case)
    
    # GET - Show current data
    if request.method == 'GET':
        enrollment_form = EnrollmentCaseForm(
            instance=enrollment_case,
            siteid=siteid  # Pass SITEID
        )
        #  WITH PREFIX
        medhisdrug_formset = MedHisDrugFormSet(
            instance=enrollment_case,
            prefix='medhisdrug_set'
        )
        underlying_form = UnderlyingConditionForm(instance=underlying)
        
        context = {
            'form': enrollment_form,
            'medhisdrug_formset': medhisdrug_formset,
            'underlying_form': underlying_form,
            'enrollment_case': enrollment_case,
            'screening_case': screening_case,
            'is_create': False,
            'is_readonly': False,
            'current_version': enrollment_case.version,
            'selected_site_id': siteid,  # Add to context
        }
        
        return render(request, 'studies/study_43en/CRF/patient/enrollment_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM
    logger.info(" Using Universal Audit System (Tier 3)")
    
    # Configure forms
    forms_config = {
        'main': {
            'class': EnrollmentCaseForm,
            'instance': enrollment_case,
            'kwargs': {'siteid': siteid}  # Pass SITEID
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
                'prefix': 'medhisdrug_set',  #  WITH PREFIX
                'related_name': 'medhisdrug_set'
            }
        }
    }
    
    # Define save callback
    def save_callback(request, forms_dict):
        return save_enrollment_and_related(
            request, forms_dict, screening_case, is_create=False
        )
    
    # Use Universal Audit System
    return process_complex_update(
        request=request,
        main_instance=enrollment_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/CRF/patient/enrollment_form.html',
        redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'enrollment_case': enrollment_case,
            'screening_case': screening_case,
            'current_version': enrollment_case.version,
            'selected_site_id': siteid,  # Add to context
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('enr_case', redirect_to='study_43en:screening_case_list')
@audit_log(model_name='ENROLLMENTCASE', get_patient_id_from='usubjid')
def enrollment_case_view(request, usubjid):
    """View enrollment (read-only) - WITH SITE FILTERING"""
    logger.info(f"=== ENROLLMENT VIEW (READ-ONLY) ===")
    
    #  Get enrollment WITH SITE FILTERING
    result = get_enrollment_with_related(request, usubjid)
    
    # Check if we got redirect response (no access)
    if result[0] is None:
        return result[1]  # Return redirect response
    
    screening_case, enrollment_case = result
    
    if not enrollment_case:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin đăng ký.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    #  Double-check site access on enrollment
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
    
    # Create readonly forms
    siteid = enrollment_case.SITEID
    enrollment_form = EnrollmentCaseForm(
        instance=enrollment_case,
        siteid=siteid  # Pass SITEID
    )
    #  WITH PREFIX
    medhisdrug_formset = MedHisDrugFormSet(
        instance=enrollment_case,
        prefix='medhisdrug_set'
    )
    underlying_form = UnderlyingConditionForm(instance=underlying)
    
    make_form_readonly(enrollment_form)
    make_formset_readonly(medhisdrug_formset)
    if underlying_form:
        make_form_readonly(underlying_form)
    
    context = {
        'form': enrollment_form,
        'medhisdrug_formset': medhisdrug_formset,
        'underlying_form': underlying_form,
        'enrollment_case': enrollment_case,
        'screening_case': screening_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': siteid,  # Add to context
    }
    
    return render(request, 'studies/study_43en/CRF/patient/enrollment_form.html', context)