# backends/studies/study_43en/views/patient/LAB/views_lab_micro.py
"""
LAB Microbiology Culture Views - REFACTORED with Semantic IDs
Features:
- Auto-generation of LAB_CULTURE_ID
- Klebsiella detection (IS_KLEBSIELLA)
- Universal Audit System
"""

import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.urls import reverse

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE, 
    ENR_CASE,
    LAB_Microbiology,
)

# Import forms
from backends.studies.study_43en.forms.patient.LAB_microbiology import (
    LABMicrobiologyCultureForm,
    LABMicrobiologyFilterForm,
    get_lab_culture_summary,
    get_kpn_positive_cultures,
)

# Import utilities
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import process_crf_update

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_enrollment_with_cultures(request, usubjid):
    """
    Get enrollment case with LAB culture records (WITH SITE FILTERING)
    
    Args:
        request: HttpRequest (for site filtering)
        usubjid: Patient USUBJID
        
    Returns:
        tuple: (screening_case, enrollment_case, cultures)
        
    Raises:
        Http404: If not found OR user lacks site access
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    # Get site filtering params
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get objects with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    enrollment_case = get_site_filtered_object_or_404(
        ENR_CASE, site_filter, filter_type, USUBJID=screening_case
    )
    
    cultures = LAB_Microbiology.objects.filter(
        USUBJID=enrollment_case
    ).select_related('USUBJID').order_by('-SPECSAMPDATE', '-LAB_CASE_SEQ')
    
    return screening_case, enrollment_case, cultures


# ==========================================
# LIST VIEW
# ==========================================

@login_required
@require_crf_view('lab_microbiology', redirect_to='study_43en:patient_list')
@audit_log(model_name='LAB_MICROBIOLOGY', get_patient_id_from='usubjid')
def microbiology_list(request, usubjid):
    """
    Display list of LAB microbiology cultures for a patient
    
    Permission: view_lab_microbiology
    Features:
    - Shows semantic LAB_CULTURE_ID
    - Highlights KPN+ cultures
    - Filter by specimen type, result, KPN status
    """
    logger.info(f"=== LAB MICROBIOLOGY LIST ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment and cultures (WITH SITE FILTERING)
    screening_case, enrollment_case, cultures = get_enrollment_with_cultures(request, usubjid)
    
    #  Site access already verified by helper function
    
    # Apply filters
    filter_form = LABMicrobiologyFilterForm(request.GET or None)
    
    if filter_form.is_valid():
        specimen_loc = filter_form.cleaned_data.get('specimen_loc')
        result = filter_form.cleaned_data.get('result')
        kpn_only = filter_form.cleaned_data.get('kpn_only')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if specimen_loc:
            cultures = cultures.filter(SPECSAMPLOC=specimen_loc)
        if result:
            cultures = cultures.filter(RESULT=result)
        if kpn_only:
            cultures = cultures.filter(IS_KLEBSIELLA=True)
        if date_from:
            cultures = cultures.filter(SPECSAMPDATE__gte=date_from)
        if date_to:
            cultures = cultures.filter(SPECSAMPDATE__lte=date_to)
    
    # Get summary statistics
    summary = get_lab_culture_summary(enrollment_case)
    
    # Get KPN+ cultures for quick access
    kpn_cultures = get_kpn_positive_cultures(enrollment_case)

    empty_form = LABMicrobiologyCultureForm(usubjid=enrollment_case)
    
    context = {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'cultures': cultures,
        'form': empty_form,
        'kpn_cultures': kpn_cultures,
        'summary': summary,
        'filter_form': filter_form,
        'specimen_choices': LAB_Microbiology.SpecimenLocationChoices.choices,
        'result_choices': LAB_Microbiology.ResultTypeChoices.choices,
        'ifpositive_choices': LAB_Microbiology.IfPositiveChoices.choices,
        'has_cultures': cultures.exists(),
        'selected_site_id': screening_case.SITEID,
    }
    
    logger.info(
        f" Loaded {cultures.count()} cultures "
        f"({summary['kpn_positive_count']} KPN+)"
    )
    return render(request, 'studies/study_43en/CRF/patient/lab_microbiology_list.html', context)


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('lab_microbiology', redirect_to='study_43en:patient_list')
@audit_log(model_name='LAB_MICROBIOLOGY', get_patient_id_from='usubjid')
def microbiology_create(request, usubjid):
    """
    Create new LAB microbiology culture
    
    Permission: add_lab_microbiology
    Features:
    - Auto-generates LAB_CASE_SEQ
    - Auto-generates LAB_CULTURE_ID
    - Auto-detects IS_KLEBSIELLA from RESULTDETAILS
    """
    logger.info(f"=== LAB MICROBIOLOGY CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment (WITH SITE FILTERING)
    screening_case, enrollment_case, _ = get_enrollment_with_cultures(request, usubjid)
    
    #  Site access already verified by helper function
    
    # POST - Process creation
    if request.method == 'POST':
        form = LABMicrobiologyCultureForm(request.POST, usubjid=enrollment_case)
        
        if form.is_valid():
            try:
                with transaction.atomic(using='db_study_43en'):
                    # Create instance
                    culture = form.save(commit=False)
                    culture.USUBJID = enrollment_case
                    
                    # LAB_CASE_SEQ, LAB_CULTURE_ID, IS_KLEBSIELLA 
                    # are auto-generated in model.save()
                    
                    # Set audit fields
                    culture.last_modified_by_id = request.user.id
                    culture.last_modified_by_username = request.user.username
                    
                    # Save (triggers auto-generation) with explicit database
                    culture.save(using='db_study_43en')
                    
                    kpn_status = "KPN+" if culture.IS_KLEBSIELLA else "KPN-"
                    logger.info(
                        f" Created: {culture.LAB_CULTURE_ID} "
                        f"({culture.get_SPECSAMPLOC_display()}) [{kpn_status}]"
                    )
                    
                    if culture.IS_KLEBSIELLA:
                        messages.success(
                            request,
                            f' Đã thêm culture {culture.LAB_CULTURE_ID} thành công! '
                            f'🔬 Đây là Klebsiella positive - có thể thêm kháng sinh đồ.'
                        )
                    else:
                        messages.success(
                            request,
                            f' Đã thêm culture {culture.LAB_CULTURE_ID} thành công!'
                        )
                    
                    return redirect('study_43en:microbiology_list', usubjid=usubjid)
            
            except Exception as e:
                logger.error(f" Error creating culture: {e}", exc_info=True)
                messages.error(request, f'Lỗi khi tạo culture: {str(e)}')
        else:
            logger.warning(f"Form validation errors: {form.errors}")
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank form
    else:
        initial = {
            'SPECSAMPDATE': date.today(),
        }
        form = LABMicrobiologyCultureForm(initial=initial, usubjid=enrollment_case)
    
    # Render with full context
    cultures = LAB_Microbiology.objects.filter(
        USUBJID=enrollment_case
    ).order_by('-SPECSAMPDATE', '-LAB_CASE_SEQ')
    
    context = {
        'form': form,
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'cultures': cultures,
        'summary': get_lab_culture_summary(enrollment_case),
        'specimen_choices': LAB_Microbiology.SpecimenLocationChoices.choices,
        'result_choices': LAB_Microbiology.ResultTypeChoices.choices,
        'ifpositive_choices': LAB_Microbiology.IfPositiveChoices.choices,
        'has_cultures': cultures.exists(),
        'is_create': True,
        'is_readonly': False,
        'selected_site_id': screening_case.SITEID,
    }
    
    return render(request, 'studies/study_43en/CRF/patient/lab_microbiology_list.html', context)


# ==========================================
# UPDATE VIEW WITH UNIVERSAL AUDIT
# ==========================================

@login_required
@require_crf_change('lab_microbiology', redirect_to='study_43en:patient_list')
@audit_log(model_name='LAB_MICROBIOLOGY', get_patient_id_from='usubjid')
def microbiology_update(request, usubjid, culture_id):
    """
    Update LAB microbiology culture WITH UNIVERSAL AUDIT SYSTEM
    
    Permission: change_lab_microbiology
    Features:
    - Tracks changes to IS_KLEBSIELLA flag
    - Updates LAB_CULTURE_ID if LAB_CASE_SEQ changes
    - Re-detects Klebsiella from RESULTDETAILS
    """
    logger.info(f"=== LAB MICROBIOLOGY UPDATE ===")
    logger.info(
        f"User: {request.user.username}, USUBJID: {usubjid}, "
        f"Culture ID: {culture_id}, Method: {request.method}"
    )
    
    # Get enrollment and culture (WITH SITE FILTERING)
    screening_case, enrollment_case, _ = get_enrollment_with_cultures(request, usubjid)
    
    culture = get_object_or_404(
        LAB_Microbiology,
        id=culture_id,
        USUBJID=enrollment_case
    )
    
    logger.info(f"Editing culture: {culture.LAB_CULTURE_ID}")
    
    #  Site access already verified by helper function
    
    # GET - Redirect to list (modal handles display)
    if request.method == 'GET':
        messages.info(request, 'Please use the edit button to modify cultures.')
        return redirect('study_43en:microbiology_list', usubjid=usubjid)
    
    # POST - USE UNIVERSAL AUDIT SYSTEM
    logger.info(" Using Universal Audit System (Tier 1)")
    
    # Custom save callback
    def save_callback(instance, form):
        """
        Handle IS_KLEBSIELLA detection and LAB_CULTURE_ID update
        Auto-generation happens in model.save()
        """
        instance.save()
        
        # Log KPN status change
        if instance.IS_KLEBSIELLA != culture.IS_KLEBSIELLA:
            old_status = "KPN+" if culture.IS_KLEBSIELLA else "KPN-"
            new_status = "KPN+" if instance.IS_KLEBSIELLA else "KPN-"
            logger.info(f"KPN status changed: {old_status} → {new_status}")
        
        return instance
    
    # Use Universal Audit System
    return process_crf_update(
        request=request,
        instance=culture,
        form_class=LABMicrobiologyCultureForm,
        template_name='studies/study_43en/CRF/patient/lab_microbiology_list.html',
        redirect_url=reverse('study_43en:microbiology_list', kwargs={'usubjid': usubjid}),
        extra_context={
            'usubjid': usubjid,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'cultures': LAB_Microbiology.objects.filter(
                USUBJID=enrollment_case
            ).order_by('-SPECSAMPDATE', '-LAB_CASE_SEQ'),
            'summary': get_lab_culture_summary(enrollment_case),
            'specimen_choices': LAB_Microbiology.SpecimenLocationChoices.choices,
            'result_choices': LAB_Microbiology.ResultTypeChoices.choices,
            'ifpositive_choices': LAB_Microbiology.IfPositiveChoices.choices,
            'selected_site_id': screening_case.SITEID,
            'edit_culture_id': culture_id,
        },
        save_callback=save_callback,
    )


# ==========================================
# GET CULTURE DATA (AJAX)
# ==========================================

@login_required
@require_crf_view('lab_microbiology', redirect_to='study_43en:patient_list')
def microbiology_get(request, usubjid, culture_id):
    """
    Get culture data as JSON for edit modal
    
    Permission: view_lab_microbiology
    Returns: JSON with culture data including LAB_CULTURE_ID and IS_KLEBSIELLA
    """
    logger.info(f"=== LAB MICROBIOLOGY GET ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Culture ID: {culture_id}")
    
    try:
        # Get enrollment and culture (WITH SITE FILTERING)
        screening_case, enrollment_case, _ = get_enrollment_with_cultures(request, usubjid)
        
        culture = get_object_or_404(
            LAB_Microbiology,
            id=culture_id,
            USUBJID=enrollment_case
        )
        
        #  Site access already verified by helper function
        
        # Format dates
        sample_date = culture.SPECSAMPDATE.isoformat() if culture.SPECSAMPDATE else ''
        isolation_date = culture.BACSTRAINISOLDATE.isoformat() if culture.BACSTRAINISOLDATE else ''
        
        data = {
            'success': True,
            'data': {
                'id': culture.id,
                'LAB_CULTURE_ID': culture.LAB_CULTURE_ID,  #  Semantic ID
                'LAB_CASE_SEQ': culture.LAB_CASE_SEQ,
                'STUDYID': culture.STUDYID or '',
                'SITEID': culture.SITEID or '',
                'SUBJID': culture.SUBJID or '',
                'INITIAL': culture.INITIAL or '',
                'SPECSAMPLOC': culture.SPECSAMPLOC,
                'OTHERSPECIMEN': culture.OTHERSPECIMEN or '',
                'SPECIMENID': culture.SPECIMENID or '',
                'SPECSAMPDATE': sample_date,
                'BACSTRAINISOLDATE': isolation_date,
                'RESULT': culture.RESULT or '',
                'IFPOSITIVE': culture.IFPOSITIVE or '',
                'SPECIFYOTHERSPECIMEN': culture.SPECIFYOTHERSPECIMEN or '',
                'RESULTDETAILS': culture.RESULTDETAILS or '',
                'IS_KLEBSIELLA': culture.IS_KLEBSIELLA,  #  KPN flag
                'ORDEREDBYDEPT': culture.ORDEREDBYDEPT or '',
                'DEPTDIAGSENT': culture.DEPTDIAGSENT or '',
                'version': culture.version,
                # For display
                'specimen_display': culture.get_SPECSAMPLOC_display(),
                'result_display': culture.get_RESULT_display() if culture.RESULT else '',
                'is_testable': culture.is_testable_for_antibiotics,  #  Can add antibiotics?
            }
        }
        
        logger.info(f" Retrieved culture data for {culture.LAB_CULTURE_ID}")
        return JsonResponse(data)
    
    except Exception as e:
        logger.error(f" Error getting culture: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)