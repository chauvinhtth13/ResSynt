# backends/studies/study_43en/views//patient/views_SCR.py
"""
Screening views - Using audit processors and permission decorators
"""
import logging
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from backends.studies.study_43en.models.patient import SCR_CASE


# Permission utilities
from backends.studies.study_43en.utils.permission_decorators import (
    require_crf_view,
)

logger = logging.getLogger(__name__)
# backends/studies/study_43en/views/patient/views_scr_case_list.py

# backends/studies/study_43en/views/patient/views_SCR.py

@login_required
@require_crf_view('scr_case', redirect_to='study_43en:home_dashboard')
def screening_case_list(request):
    """
    List screening cases with site selection modal
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_filtered_queryset
    )
    from backends.tenancy.models import StudySite
    
    #  CRITICAL FIX: Declare these variables FIRST
    study = getattr(request, 'study', None)
    user_sites = getattr(request, 'user_sites', set())
    can_access_all = getattr(request, 'can_access_all_sites', False)
    
    # Get query params
    enrolled = request.GET.get('enrolled', '') == 'true'
    query = request.GET.get('q', '').strip()
    
    # Get site filtering parameters
    site_filter, filter_type = get_site_filter_params(request)
    selected_site_id = request.session.get('selected_site_id', 'all')
    
    logger.info(f" Site filter: {site_filter}, type: {filter_type}")
    
    # Apply site filtering
    cases = get_filtered_queryset(SCR_CASE, site_filter, filter_type)
    
    logger.info(f" Filtered cases count: {cases.count()}")
    logger.info(f" First 5 cases SITEIDs: {[c.SITEID for c in cases[:5]]}")

    # Filter enrolled cases
    if enrolled:
        cases = cases.filter(
            UPPER16AGE=True,
            INFPRIOR2OR48HRSADMIT=True,
            ISOLATEDKPNFROMINFECTIONORBLOOD=True,
            KPNISOUNTREATEDSTABLE=False,
            CONSENTTOSTUDY=True
        )

    def normalize_SCRID(sid):
        """Extract numeric part from SCRID for sorting"""
        match = re.match(r'PS-\d+-(\d+)', sid or '')
        if match:
            return int(match.group(1))
        match = re.match(r'PS0*(\d+)', sid or '')
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

    # Sort
    site_order = {'003': 0, '020': 1, '011': 2}
    cases = sorted(cases, key=lambda c: (
        site_order.get(c.SITEID, 999),
        normalize_SCRID(c.SCRID)
    ))

    # Statistics
    total_cases = len(cases)
    eligible_cases = len([
        c for c in cases if 
        c.UPPER16AGE and c.INFPRIOR2OR48HRSADMIT and 
        c.ISOLATEDKPNFROMINFECTIONORBLOOD and 
        not c.KPNISOUNTREATEDSTABLE and c.CONSENTTOSTUDY
    ])

    #  Get available sites for modal (NOW study is defined)
    available_sites = []
    if study:
        try:
            # Query StudySite from DEFAULT database
            study_sites = StudySite.objects.using('default').filter(
                study=study
            ).select_related('site').order_by('site__code')
            
            logger.info(f"Found {study_sites.count()} sites for study {study.code}")
            
            # Filter based on user permissions
            if can_access_all:
                available_sites = list(study_sites)
                logger.info(f"Admin: showing all {len(available_sites)} sites")
            elif user_sites:
                available_sites = [ss for ss in study_sites if ss.site.code in user_sites]
                logger.info(f"User: showing {len(available_sites)} of {study_sites.count()} sites")
            else:
                logger.warning(f"User has no sites assigned")
                available_sites = []
                
        except Exception as e:
            logger.error(f"Error loading sites: {e}", exc_info=True)
            available_sites = []
    else:
        logger.warning("No study context available")
    
    logger.info(f"Available sites for modal: {[ss.site.code for ss in available_sites]}")

    # Pagination
    paginator = Paginator(cases, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Convert to list for template
    user_sites_list = sorted(list(user_sites))

    return render(request, 'studies/study_43en/CRF/patient/screening_case_list.html', {
        'page_obj': page_obj,
        'total_cases': total_cases,
        'eligible_cases': eligible_cases,
        'query': query,
        'view_type': 'enrolled' if enrolled else 'screening',
        'selected_site_id': selected_site_id,
        'user_sites': user_sites_list,
        'available_sites': available_sites,  #  Sites for modal
        'can_access_all': can_access_all,     #  Permission flag
    })
