# backends/studies/study_43en/views/patient/views_SCR.py
"""
Screening views - Using audit processors and permission decorators
"""
import logging
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.models.patient import SCR_CASE
from backends.studies.study_43en.forms.patient.SCR import ScreeningCaseForm
from django.contrib import messages
# Audit utilities
from backends.studies.study_43en.utils.audit.decorators import audit_log
from backends.studies.study_43en.utils.audit.processors import (
    process_crf_update,
    process_crf_create,
)

# Permission utilities
from backends.studies.study_43en.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
    check_site_permission,
)

logger = logging.getLogger(__name__)


@login_required
@require_crf_add('scr_case', redirect_to='study_43en:screening_case_list')
@audit_log(model_name='SCREENINGCASE', get_patient_id_from='SCRID')
def screening_case_create(request):
    """
    CREATE screening case - WITH SITE SELECTION MODAL
    
    Flow:
    1. User clicks "Create New" → Show modal to select site
    2. User selects site → Generate SCRID with format PS-SITEID-0001
    3. User confirms → Show form with locked SCRID, SITEID, STUDYID
    4. User fills form and submits
    """
    
    logger.info(f"=== SCREENING CREATE VIEW ===")
    logger.info(f"User: {request.user.username}")
    logger.info(f"Method: {request.method}")
    
    # Get site from session
    selected_site_id = request.session.get('selected_site_id', 'all')
    logger.info(f"Selected site from session: {selected_site_id}")
    
    # ==========================================
    # STEP 1: Get SITEID from GET parameter
    # ==========================================
    siteid = request.GET.get('siteid', '').strip()
    
    # If no siteid provided, redirect back to list (modal will handle selection)
    if not siteid:
        logger.info("No SITEID provided - user needs to select from modal")
        return redirect('study_43en:screening_case_list')
    
    # Validate SITEID format
    if siteid not in ['003', '020', '011']:
        logger.error(f"Invalid SITEID format: {siteid}")
        messages.error(request, f'Site ID không hợp lệ: {siteid}')
        return redirect('study_43en:screening_case_list')
    
    # SECURITY FIX: Check user's ACTUAL site permissions (not just session)
    if not check_site_permission(request, siteid):
        user_sites = getattr(request, 'user_sites', set())
        logger.warning(
            f"🚨 SECURITY: User {request.user.username} "
            f"(accessible_sites={user_sites}) "
            f"attempted to create screening for unauthorized site {siteid}"
        )
        messages.error(
            request,
            f'🚨 Bạn không có quyền tạo screening cho site {siteid}! '
            f'(Chỉ được tạo cho: {", ".join(sorted(user_sites)) if user_sites else "không có site nào"})'
        )
        return redirect('study_43en:screening_case_list')
    
    logger.info(f" SITEID validated: {siteid} (user has permission)")
    
    # ==========================================
    # STEP 2: Generate SCRID
    # ==========================================
    site_cases = SCR_CASE.objects.filter(
        SCRID__startswith=f'PS-{siteid}-'
    ).values_list('SCRID', flat=True)
    
    max_num = 0
    for sid in site_cases:
        m = re.match(rf'PS-{siteid}-(\d+)', str(sid))
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    
    new_scrid = f"PS-{siteid}-{max_num + 1:04d}"
    logger.info(f"Generated new SCRID: {new_scrid}")
    
    # ==========================================
    # STEP 3: Handle POST (Form Submission)
    # ==========================================
    def pre_save(instance):
        """Ensure SCRID and SITEID are set"""
        instance.SCRID = new_scrid
        instance.SITEID = siteid
        logger.info(f"Pre-save: SCRID={instance.SCRID}, SITEID={instance.SITEID}")
    
    def post_save(instance):
        """Redirect to enrollment if confirmed"""
        if instance.is_confirmed and instance.USUBJID:
            logger.info(f"Patient confirmed - redirecting to enrollment: {instance.USUBJID}")
            return redirect(
                'study_43en:enrollment_case_create',
                usubjid=instance.USUBJID
            )
        return None
    
    if request.method == 'POST':
        logger.info("Processing POST request")
        return process_crf_create(
            request=request,
            form_class=ScreeningCaseForm,
            template_name='studies/study_43en/CRF/patient/screening_form.html',
            redirect_url='study_43en:screening_case_list',
            pre_save_callback=pre_save,
            post_save_callback=post_save,
            extra_context={
                'selected_site_id': selected_site_id,
                'scrid_locked': True,
                'siteid_locked': True,
            },
            form_kwargs={'selected_site_id': siteid}  # Pass actual site, not 'all'
        )
    
    # ==========================================
    # STEP 4: Show Form (GET)
    # ==========================================
    logger.info("Showing form for GET request")
    
    # Create instance with generated SCRID
    instance = SCR_CASE(SCRID=new_scrid, SITEID=siteid)
    
    # Initial data
    initial_data = {
        'STUDYID': '43EN',
        'SITEID': siteid,
    }
    
    # Create form
    form = ScreeningCaseForm(
        instance=instance,
        initial=initial_data,
        selected_site_id=siteid  # Pass actual site
    )
    
    # Lock SCRID and SITEID fields (STUDYID already locked in form __init__)
    if 'SCRID' in form.fields:
        form.fields['SCRID'].widget.attrs['readonly'] = True
        form.fields['SCRID'].widget.attrs['style'] = 'background-color: #e9ecef; font-weight: bold;'
        form.fields['SCRID'].disabled = True
    
    form.fields['SITEID'].widget.attrs['readonly'] = True
    form.fields['SITEID'].widget.attrs['style'] = 'background-color: #e9ecef;'
    form.fields['SITEID'].disabled = True
    
    # STUDYID is already locked in form __init__ with readonly (not disabled)
    # This ensures the value is included in POST
    
    logger.info("Form created with locked fields")
    
    return render(request, 'studies/study_43en/CRF/patient/screening_form.html', {
        'form': form,
        'is_create': True,
        'selected_site_id': selected_site_id,
        'scrid_locked': True,
        'siteid_locked': True,
        'current_scrid': new_scrid,
        'current_siteid': siteid,
    })


@login_required
@require_crf_change('scr_case', redirect_to='study_43en:screening_case_list')
@audit_log(model_name='SCREENINGCASE', get_patient_id_from='SCRID')
def screening_case_update(request, SCRID):
    """
    UPDATE screening case
    Permission: change_screeningcase
    
     FIXED: Use site filtering to get instance
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    logger.info(f"=== SCREENING UPDATE VIEW ===")
    logger.info(f"User: {request.user.username}")
    logger.info(f"SCRID: {SCRID}")
    logger.info(f"Method: {request.method}")
    
    # Get site filtering params
    site_filter, filter_type = get_site_filter_params(request)
    selected_site_id = request.session.get('selected_site_id', 'all')
    
    #  Get instance WITH SITE FILTERING
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE,
        site_filter,
        filter_type,
        SCRID=SCRID
    )
    
    logger.info(f" Site access verified (filter: {site_filter}, type: {filter_type})")
    
    #  GET - FIXED: Pass selected_site_id to form
    if request.method == 'GET':
        form = ScreeningCaseForm(
            instance=screening_case,
            selected_site_id=selected_site_id  #  THÊM
        )
        
        return render(request, 'studies/study_43en/CRF/patient/screening_form.html', {
            'form': form,
            'is_create': False,
            'scrid': SCRID,
            'current_version': screening_case.version,
            'selected_site_id': selected_site_id,
        })
    
    #  POST - FIXED: Pass form_kwargs to processor
    return process_crf_update(
        request=request,
        instance=screening_case,
        form_class=ScreeningCaseForm,
        template_name='studies/study_43en/CRF/patient/screening_form.html',
        redirect_url='study_43en:screening_case_list',
        form_kwargs={'selected_site_id': selected_site_id},  #  THÊM
        extra_context={
            'scrid': SCRID,
            'selected_site_id': selected_site_id,
        }
    )


@login_required
@require_crf_view('scr_case', redirect_to='study_43en:screening_case_list')
@audit_log(model_name='SCREENINGCASE', get_patient_id_from='SCRID')
def screening_case_view(request, SCRID):
    """
    READ screening case (read-only)
    Permission: view_screeningcase
    
     FIXED: Use site filtering to get instance
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    # Get site filtering params
    site_filter, filter_type = get_site_filter_params(request)
    selected_site_id = request.session.get('selected_site_id', 'all')
    
    #  Get instance WITH SITE FILTERING
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE,
        site_filter,
        filter_type,
        SCRID=SCRID
    )
    
    #  FIXED: Pass selected_site_id to form
    form = ScreeningCaseForm(
        instance=screening_case,
        selected_site_id=selected_site_id  #  THÊM
    )
    
    # Make read-only
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    return render(request, 'studies/study_43en/CRF/patient/screening_form.html', {
        'form': form,
        'is_create': False,
        'is_readonly': True,
        'scrid': SCRID,
        'screening_case': screening_case,
        'selected_site_id': selected_site_id,
    })