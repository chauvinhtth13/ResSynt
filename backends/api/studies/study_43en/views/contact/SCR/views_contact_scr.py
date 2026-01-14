# backends/studies/study_43en/views/contact/views_SCR.py
"""
Contact Screening views - Using audit processors and permission decorators
"""
import logging
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from backends.studies.study_43en.models.contact import SCR_CONTACT
from backends.studies.study_43en.forms.contact.contact_SCR import ScreeningContactForm
from backends.studies.study_43en.models import AuditLog, AuditLogDetail

# Audit utilities
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import (
    process_crf_update,
    process_crf_create,
)

# Permission utilities
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
    check_site_permission,
)

logger = logging.getLogger(__name__)


# ==========================================
# LIST VIEW
# ==========================================

@login_required
@require_crf_view('scr_contact', redirect_to='study_43en:home_dashboard')
def screening_contact_list(request):
    """
    List contact screening cases
    Permission: view_screeningcontact
    """
    enrolled = request.GET.get('enrolled', '') == 'true'
    query = request.GET.get('q', '').strip()
    site_id = request.session.get('selected_site_id', 'all')

    #  Apply site filtering properly
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_filtered_queryset
    )
    
    site_filter, filter_type = get_site_filter_params(request)
    cases = get_filtered_queryset(SCR_CONTACT, site_filter, filter_type)

    # Filter enrolled contacts (3 criteria)
    if enrolled:
        cases = cases.filter(
            LIVEIN5DAYS3MTHS=True,
            MEALCAREONCEDAY=True,
            CONSENTTOSTUDY=True
        )

    def normalize_SCRID(sid):
        """Extract numeric part from SCRID for sorting"""
        # Support both old (CS0001) and new (CS-003-0001) formats
        match = re.match(r'CS-\d+-(\d+)', sid or '')  # New format: CS-003-0001
        if match:
            return int(match.group(1))
        match = re.match(r'CS0*(\d+)', sid or '')  # Old format: CS0001
        return int(match.group(1)) if match else -1

    # Search
    if query:
        try:
            query_num = int(query)
            cases = [c for c in cases if normalize_SCRID(c.SCRID) == query_num]
        except ValueError:
            cases = [c for c in cases if 
                     query.lower() in (c.SCRID or '').lower() or 
                     query.lower() in (c.USUBJID or '').lower() or 
                     query.lower() in (c.INITIAL or '').lower()]

    # Sort by SITEID first (003, 020, 011), then by SCRID number
    site_order = {'003': 0, '020': 1, '011': 2}
    cases = sorted(cases, key=lambda c: (
        site_order.get(c.SITEID, 999),  # Sort by site priority
        normalize_SCRID(c.SCRID)        # Then by SCRID number
    ))

    # Statistics (3 criteria for contacts)
    total_cases = len(cases)
    eligible_cases = len([
        c for c in cases if 
        c.LIVEIN5DAYS3MTHS and 
        c.MEALCAREONCEDAY and 
        c.CONSENTTOSTUDY
    ])

    # Pagination
    paginator = Paginator(cases, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Get user's accessible sites from middleware
    user_sites = getattr(request, 'user_sites', set())
    user_sites_list = sorted(list(user_sites))  # Convert to sorted list for template

    return render(request, 'studies/study_43en/contact/list/screening_contact_list.html', {
        'page_obj': page_obj,
        'total_cases': total_cases,
        'eligible_cases': eligible_cases,
        'query': query,
        'view_type': 'enrolled' if enrolled else 'screening',
        'selected_site_id': site_id,  # Pass site_id to template for modal
        'user_sites': user_sites_list,  # Pass user's accessible sites to template
    })


# ==========================================
# CREATE VIEW
# ==========================================

@login_required
@require_crf_add('scr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(
    model_name='SCREENINGCONTACT',
    get_patient_id_from='SCRID',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def screening_contact_create(request):
    """
    CREATE contact screening case - WITH SITE SELECTION MODAL
    Permission: add_screeningcontact
    
     NEW: Requires siteid parameter from modal (e.g., ?siteid=003)
    """
    from django.contrib import messages
    from django.utils.translation import gettext_lazy as _
    
    # Get siteid from GET parameter (from modal)
    siteid = request.GET.get('siteid', '').strip()
    
    # Validate siteid exists
    if not siteid:
        messages.error(request, _('❌ Missing SITEID. Please select a site first.'))
        return redirect('study_43en:screening_contact_list')
    
    # Validate siteid format
    if siteid not in ['003', '020', '011']:
        messages.error(request, _('❌ Invalid SITEID. Must be 003, 020, or 011.'))
        return redirect('study_43en:screening_contact_list')
    
    # 🔒 SECURITY FIX: Check user's ACTUAL site permissions (not just session)
    if not check_site_permission(request, siteid):
        user_sites = getattr(request, 'user_sites', set())
        logger.warning(
            f"🚨 SECURITY: User {request.user.username} "
            f"(accessible_sites={user_sites}) "
            f"attempted to create contact screening for unauthorized site {siteid}"
        )
        messages.error(
            request,
            f'🚨 Bạn không có quyền tạo contact screening cho site {siteid}! '
            f'(Chỉ được tạo cho: {", ".join(sorted(user_sites)) if user_sites else "không có site nào"})'
        )
        return redirect('study_43en:screening_contact_list')
    
    logger.info(f" Creating contact screening for site {siteid} (user has permission)")
    
    def pre_save(instance):
        """Set SITEID and generate SCRID with new format"""
        instance.SITEID = siteid  # Set from URL parameter
        
        # Generate SCRID if not set (format: CS-SITEID-0001)
        if not instance.SCRID:
            site_contacts = SCR_CONTACT.objects.filter(
                SCRID__startswith=f'CS-{siteid}-'
            ).values_list('SCRID', flat=True)
            
            max_num = 0
            for scrid in site_contacts:
                m = re.match(rf'CS-{siteid}-(\d+)', str(scrid))
                if m:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
            
            instance.SCRID = f"CS-{siteid}-{max_num + 1:04d}"
            logger.info(f"📝 Generated Contact SCRID: {instance.SCRID}")
    
    def post_save(instance):
        """Redirect to enrollment if confirmed"""
        if instance.is_confirmed and instance.USUBJID:
            return redirect(
                'study_43en:enrollment_contact_create',
                usubjid=instance.USUBJID
            )
        return None
    
    if request.method == 'POST':
        return process_crf_create(
            request=request,
            form_class=ScreeningContactForm,
            template_name='studies/study_43en/contact/form/screening_contact_form.html',
            redirect_url='study_43en:screening_contact_list',
            pre_save_callback=pre_save,
            post_save_callback=post_save,
            extra_context={'selected_site_id': siteid}
        )
    
    # GET - Create blank instance with SCRID preview
    # Generate SCRID for preview
    site_contacts = SCR_CONTACT.objects.filter(
        SCRID__startswith=f'CS-{siteid}-'
    ).values_list('SCRID', flat=True)
    
    max_num = 0
    for scrid in site_contacts:
        m = re.match(rf'CS-{siteid}-(\d+)', str(scrid))
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    
    new_SCRID = f"CS-{siteid}-{max_num + 1:04d}"
    instance = SCR_CONTACT(SCRID=new_SCRID, SITEID=siteid)
    
    initial_data = {'STUDYID': '43EN', 'SITEID': siteid}
    
    form = ScreeningContactForm(instance=instance, initial=initial_data)
    
    return render(request, 'studies/study_43en/contact/form/screening_contact_form.html', {
        'form': form,
        'is_create': True,
        'selected_site_id': siteid,  # Show specific site
        'siteid': siteid,  # Pass siteid to template
    })


# ==========================================
# UPDATE VIEW
# ==========================================

@login_required
@require_crf_change('scr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(
    model_name='SCREENINGCONTACT',
    get_patient_id_from='SCRID',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def screening_contact_update(request, SCRID):
    """
    UPDATE contact screening case
    Permission: change_screeningcontact
    """
    logger.info(f"=== CONTACT SCREENING UPDATE VIEW ===")
    logger.info(f"User: {request.user.username}")
    logger.info(f"SCRID: {SCRID}")
    logger.info(f"Method: {request.method}")
    
    # Get instance (WITH SITE FILTERING)
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    site_filter, filter_type = get_site_filter_params(request)
    screening_contact = get_site_filtered_object_or_404(
        SCR_CONTACT, site_filter, filter_type, SCRID=SCRID
    )
    
    logger.info(f" Site access verified, all checks passed")
    
    # GET - Show form
    if request.method == 'GET':
        form = ScreeningContactForm(instance=screening_contact)
        
        # Get selected site from session
        selected_site_id = request.session.get('selected_site_id', 'all')
        
        return render(request, 'studies/study_43en/contact/form/screening_contact_form.html', {
            'form': form,
            'is_create': False,
            'scrid': SCRID,
            'current_version': screening_contact.version,
            'selected_site_id': selected_site_id,  # ADD THIS
        })
    
    # POST - Process update
    return process_crf_update(
        request=request,
        instance=screening_contact,
        form_class=ScreeningContactForm,
        template_name='studies/study_43en/contact/form/screening_contact_form.html',
        redirect_url='study_43en:screening_contact_list',
        extra_context={
            'scrid': SCRID,
            'selected_site_id': request.session.get('selected_site_id', 'all'),  # ADD THIS
        }
    )


# ==========================================
# VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('scr_contact', redirect_to='study_43en:screening_contact_list')
@audit_log(
    model_name='SCREENINGCONTACT',
    get_patient_id_from='SCRID',
    patient_model=SCR_CONTACT,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def screening_contact_view(request, SCRID):
    """
    READ contact screening case (read-only)
    Permission: view_screeningcontact
    """
    # Get instance (WITH SITE FILTERING)
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    site_filter, filter_type = get_site_filter_params(request)
    screening_contact = get_site_filtered_object_or_404(
        SCR_CONTACT, site_filter, filter_type, SCRID=SCRID
    )
    
    # Create read-only form
    form = ScreeningContactForm(instance=screening_contact)
    
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    return render(request, 'studies/study_43en/contact/form/screening_contact_form.html', {
        'form': form,
        'is_create': False,
        'is_readonly': True,
        'scrid': SCRID,
        'screening_contact': screening_contact,
        'selected_site_id': request.session.get('selected_site_id', 'all'),  # ADD THIS
    })
