"""
Dashboard Views for Study 43EN - COMPLETELY NEW & SIMPLIFIED
=============================================================

Following GUIDE.txt principles:
 BACKEND-FIRST: All logic in Django
 NO JavaScript logic: Pure backend data processing
 Clean structure: Models → Views → Templates
 Proper error handling with logging
 Optimized queries with select_related/prefetch_related

Version: 2.0 (Complete rewrite)
Author: Claude
Date: 2026-01-13
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField, Q
from django.utils.translation import gettext as _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from functools import wraps
import logging

# Import site utilities
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset
)

# Import models
from backends.studies.study_43en.models import (
    SCR_CASE,       # Patient screening
    ENR_CASE,       # Patient enrollment
    SCR_CONTACT,    # Contact screening
    ENR_CONTACT,    # Contact enrollment
)

# Import tenancy models (for site/study info)
from backends.tenancy.models import Site, Study, StudySite

# Import sample models (with fallback)
try:
    from backends.studies.study_43en.models.patient.SAM_CASE import SAM_CASE
    from backends.studies.study_43en.models.contact.SAM_CONTACT import SAM_CONTACT
except ImportError:
    SAM_CASE = None
    SAM_CONTACT = None

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

DB_ALIAS = 'db_study_43en'
STUDY_CODE = '43EN'

# Site configuration for enrollment targets
SITE_CONFIG = {
    'all': {'target': 750, 'start_date': date(2024, 7, 1)},
    '003': {'target': 200, 'start_date': date(2024, 7, 1)},
    '011': {'target': 400, 'start_date': date(2025, 10, 13)},
    '020': {'target': 150, 'start_date': date(2025, 11, 5)},
}

SITE_NAMES = {'003': 'HTD', '020': 'NHTD', '011': 'Cho Ray'}

# Study timeline
STUDY_START_DATE = date(2024, 7, 1)
STUDY_END_DATE = date(2027, 4, 30)
CHART_END_DATE = date(2027, 5, 1)
TOTAL_STUDY_MONTHS = 35


# ============================================================================
# DYNAMIC SITE CODES HELPER
# ============================================================================

def get_study_site_codes(request):
    """
    Get all site codes linked to the current study from StudySite.
    
    Args:
        request: HTTP request with study info from middleware
    
    Returns:
        tuple: Site codes linked to current study, e.g. ('003', '011', '020')
    """
    study = getattr(request, 'study', None)
    
    if study:
        # Get sites from StudySite relationship
        site_codes = StudySite.objects.filter(
            study=study
        ).values_list('site__code', flat=True)
        return tuple(sorted(site_codes))
    
    # Fallback: try to get study by STUDY_CODE
    try:
        study_obj = Study.objects.get(code=STUDY_CODE)
        site_codes = StudySite.objects.filter(
            study=study_obj
        ).values_list('site__code', flat=True)
        return tuple(sorted(site_codes))
    except Study.DoesNotExist:
        logger.warning(f"Study {STUDY_CODE} not found, using empty site codes")
        return ()


def get_site_names_from_db(request):
    """
    Get site names mapping from database.
    
    Returns:
        dict: {site_code: abbreviation} e.g. {'003': 'HTD', '020': 'NHTD'}
    """
    study = getattr(request, 'study', None)
    
    if study:
        sites = Site.objects.filter(
            site_studies__study=study
        ).values('code', 'abbreviation')
        return {s['code']: s['abbreviation'] for s in sites}
    
    # Fallback to constant
    return SITE_NAMES


# ============================================================================
# SECURITY HELPERS
# ============================================================================

def get_user_site_context(request):
    """
    Extract user's site permissions from request (set by middleware).
    
    Returns:
        tuple: (user_sites: set, can_access_all: bool)
    """
    return (
        getattr(request, 'user_sites', set()),
        getattr(request, 'can_access_all_sites', False)
    )


def build_allowed_sites_list(request, user_sites, can_access_all):
    """
    Build list of sites user can access for dropdown/API.
    
    Args:
        request: HttpRequest (for getting study's linked sites)
        user_sites: set of site codes
        can_access_all: bool
        
    Returns:
        list: Site codes with 'all' option if applicable
    """
    study_site_codes = get_study_site_codes(request)
    
    if can_access_all:
        return ['all'] + list(study_site_codes)
    elif user_sites and len(user_sites) > 1:
        return ['all'] + sorted(user_sites)
    elif user_sites:
        return sorted(user_sites)
    return []


def validate_site_access(request, site_code):
    """
    Validate user has permission to access a specific site.
    
    Args:
        request: HttpRequest
        site_code: str - site code to validate
        
    Returns:
        tuple: (is_valid: bool, error_response: JsonResponse or None)
    """
    if site_code == 'all':
        return True, None
        
    user_sites, can_access_all = get_user_site_context(request)
    
    if can_access_all or site_code in user_sites:
        return True, None
    
    logger.warning(
        f"Access denied: User {request.user.username} attempted to access site {site_code}"
    )
    return False, JsonResponse({
        'success': False,
        'error': f'Bạn không có quyền truy cập site {site_code}',
        'allowed_sites': build_allowed_sites_list(request, user_sites, can_access_all),
    }, status=403)


def get_site_filter_with_validation(request):
    """
    Get site filter from request parameter or middleware, with validation.
    
    Args:
        request: HttpRequest
        
    Returns:
        tuple: (site_filter, filter_type, allowed_sites, error_response)
               error_response is None if valid
    """
    user_sites, can_access_all = get_user_site_context(request)
    allowed_sites = build_allowed_sites_list(request, user_sites, can_access_all)
    
    site_param = request.GET.get('site')
    
    if site_param and site_param != 'all':
        is_valid, error = validate_site_access(request, site_param)
        if not is_valid:
            return None, None, allowed_sites, error
        return site_param, 'single', allowed_sites, None
    
    site_filter, filter_type = get_site_filter_params(request)
    return site_filter, filter_type, allowed_sites, None


# ============================================================================
# MAIN MANAGEMENT REPORT VIEW
# ============================================================================

@login_required
def management_report(request):
    """
    Management Report view - BACKEND ONLY
    
    Shows:
    - Screening patients count
    - Enrolled patients count
    - Screening contacts count
    - Enrolled contacts count
    
    All filtered by site from UnifiedTenancyMiddleware
    
    Args:
        request: HttpRequest with site context from middleware
        
    Returns:
        Rendered management report template with statistics
    """
    # DEBUG: Log request attributes from middleware
    logger.info(f"Management Report - request.study: {getattr(request, 'study', 'NOT SET')}")
    logger.info(f"Management Report - request.user_sites: {getattr(request, 'user_sites', 'NOT SET')}")
    logger.info(f"Management Report - request.can_access_all_sites: {getattr(request, 'can_access_all_sites', 'NOT SET')}")
    
    # Get site filter from middleware context
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"Management Report loading - Site: {site_filter}, Type: {filter_type}")
    
    try:
        # ===== OPTIMIZED: Single aggregation query for patient stats =====
        # Instead of 2 separate count queries, use Case/When aggregation
        # Note: SCR_CASE uses USUBJID as primary key, not 'id' - use 'pk' instead
        patient_qs = get_filtered_queryset(SCR_CASE, site_filter, filter_type)
        patient_stats = patient_qs.aggregate(
            screening_patients=Count('pk'),
            enrolled_patients=Count(
                Case(
                    When(
                        UPPER16AGE=True,
                        INFPRIOR2OR48HRSADMIT=True,
                        ISOLATEDKPNFROMINFECTIONORBLOOD=True,
                        KPNISOUNTREATEDSTABLE=False,
                        CONSENTTOSTUDY=True,
                        is_confirmed=True,
                        then=1
                    ),
                    output_field=IntegerField()
                )
            )
        )
        screening_patients = patient_stats['screening_patients']
        enrolled_patients = patient_stats['enrolled_patients']
        
        logger.debug(f"Patients - Screening: {screening_patients}, Enrolled: {enrolled_patients}")
        
        # ===== OPTIMIZED: Single aggregation query for contact stats =====
        # Instead of 2 separate count queries for SCR_CONTACT and ENR_CONTACT
        screening_contacts = get_filtered_queryset(
            SCR_CONTACT,
            site_filter,
            filter_type
        ).count()
        
        enrolled_contacts = get_filtered_queryset(
            ENR_CONTACT,
            site_filter,
            filter_type
        ).count()
        
        logger.debug(f"Contacts - Screening: {screening_contacts}, Enrolled: {enrolled_contacts}")
        
        # ===== SITE PERMISSIONS =====
        user_sites, can_access_all = get_user_site_context(request)
        accessible_sites = build_allowed_sites_list(request, user_sites, can_access_all)
        # Remove 'all' from accessible_sites for dropdown (it's added separately in template)
        accessible_sites = [s for s in accessible_sites if s != 'all']
        
        logger.debug(f"Site permissions - user_sites: {user_sites}, can_access_all: {can_access_all}")
        
        # ===== SITE NAME GENERATION =====
        site_name = _get_site_display_name(site_filter, filter_type)
        
        # ===== STUDY NAME - From Database =====
        study_name = _get_study_name(request)
        
        # ===== BUILD CONTEXT =====
        context = {
            # Study metadata
            'study': getattr(request, 'study', None),
            'study_code': '43en',
            'study_folder': 'studies/study_43en',
            'study_name': study_name,
            
            # Site information
            'site_name': site_name,
            'site_filter': site_filter,
            'filter_type': filter_type,
            'accessible_sites': accessible_sites,  # NEW: For dropdown
            'can_access_all_sites': can_access_all,  # NEW: For UI logic
            
            # Statistics
            'screening_patients': screening_patients,
            'enrolled_patients': enrolled_patients,
            'screening_contacts': screening_contacts,
            'enrolled_contacts': enrolled_contacts,
            
            # Metadata
            'today': datetime.now(),
        }
        
        logger.info(
            f"Management Report loaded successfully - "
            f"Patients: {screening_patients}/{enrolled_patients}, "
            f"Contacts: {screening_contacts}/{enrolled_contacts}"
        )
        
        return render(request, 'studies/study_43en/base/management_report.html', context)
        
    except Exception as e:
        logger.error(f"Management Report error: {str(e)}", exc_info=True)
        
        # Return error context
        return render(request, 'studies/study_43en/base/management_report.html', {
            'error': str(e),
            'today': datetime.now(),
            'study_folder': 'studies/study_43en',
            'study_code': '43en',
        })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_study_name(request):
    """
    Get study name from database based on current study context.
    
    Args:
        request: HttpRequest with study context from middleware
        
    Returns:
        str: Study name in current language (vi/en), empty string if not found
    """
    try:
        # Try to get study from request context (set by middleware)
        study = getattr(request, 'study', None)
        if study:
            # Check name property first (handles language switching)
            for attr in ('name', 'name_en', 'name_vi'):
                name = getattr(study, attr, None)
                if name and name.strip():
                    return name
        
        # Fallback: Query by study code
        study = Study.objects.filter(code=STUDY_CODE).values('name_en', 'name_vi').first()
        if study:
            return study.get('name_en') or study.get('name_vi') or ""
        
        logger.warning("Study name not found in database")
        return ""
        
    except Exception as e:
        logger.warning(f"Could not fetch study name: {e}")
        return ""


def _get_site_display_name(site_filter, filter_type):
    """
    Generate human-readable site name for display.
    
    Format:
    - All Sites: "All Sites" / "Tất cả các site"
    - Single site: "003 - HTD" (mã site - tên viết tắt)
    - Multiple sites: "003 - HTD | 011 - CR"
    
    Args:
        site_filter: 'all' | str | list
        filter_type: 'all' | 'single' | 'multiple'
        
    Returns:
        str: Display name
    """
    # All Sites case
    if filter_type == 'all' or site_filter == 'all':
        return _("All Sites")
    
    try:
        if filter_type == 'single':
            site = Site.objects.filter(code=site_filter).values('code', 'abbreviation').first()
            if site:
                return f"{site['code']} - {site['abbreviation']}" if site['abbreviation'] else site['code']
            return f"Site {site_filter}"
            
        elif filter_type == 'multiple':
            site_codes = site_filter if isinstance(site_filter, list) else list(site_filter)
            sites = Site.objects.filter(code__in=site_codes).values('code', 'abbreviation').order_by('code')
            
            if not sites:
                return _("No Sites")
            
            site_names = [
                f"{s['code']} - {s['abbreviation']}" if s['abbreviation'] else s['code']
                for s in sites
            ]
            return " | ".join(site_names)
                    
    except Exception as e:
        logger.warning(f"Could not fetch site name: {e}")
        if filter_type == 'single':
            return f"Site {site_filter}"
        elif filter_type == 'multiple' and site_filter:
            return f"{len(site_filter)} Sites"
    
    return _("All Sites")


def _generate_month_labels(start_date, end_date):
    """
    Generate list of month labels and date objects.
    
    Args:
        start_date: date - start of range
        end_date: date - end of range
        
    Returns:
        tuple: (months: list[str], month_dates: list[date])
    """
    months = []
    month_dates = []
    current = start_date.replace(day=1)
    end = end_date.replace(day=1)
    
    while current <= end:
        months.append(current.strftime('%m/%Y'))
        month_dates.append(current)
        current += relativedelta(months=1)
    
    return months, month_dates


def _calculate_target_cumulative(filter_type, site_filter, site_target, site_start_date, month_dates):
    """
    Calculate cumulative target enrollment for chart.
    
    Args:
        filter_type: 'all' | 'single' | 'multiple'
        site_filter: site code(s)
        site_target: int - total target
        site_start_date: date - when site started
        month_dates: list of date objects
        
    Returns:
        list: Cumulative target values (None for months before site start)
    """
    target_cumulative = []
    cumulative = 0.0
    
    if filter_type == 'all' or site_filter == 'all':
        # Phase 1 (07/2024-06/2025): 15/month, Phase 2: 25/month
        phase_1_end = date(2025, 6, 30)
        
        for month_date in month_dates:
            cumulative += 15 if month_date <= phase_1_end else 25
            target_cumulative.append(round(cumulative))
        
        # Ensure last value is exactly 750
        if target_cumulative:
            target_cumulative[-1] = 750
    else:
        # Individual sites: distribute evenly
        site_start_month = site_start_date.replace(day=1)
        
        # Count available months
        available_months = sum(1 for d in month_dates if d >= site_start_month)
        monthly_step = site_target / available_months if available_months > 0 else 0
        
        for month_date in month_dates:
            if month_date < site_start_month:
                target_cumulative.append(None)
            else:
                cumulative += monthly_step
                target_cumulative.append(round(cumulative))
        
        # Ensure last non-null value is exactly the target
        non_null_indices = [i for i, v in enumerate(target_cumulative) if v is not None]
        if non_null_indices:
            target_cumulative[non_null_indices[-1]] = int(site_target)
    
    return target_cumulative


def _calculate_actual_cumulative(site_filter, filter_type, months, month_dates):
    """
    Calculate actual cumulative enrollment from database.
    
    Args:
        site_filter: site code(s)
        filter_type: 'all' | 'single' | 'multiple'
        months: list of month labels (MM/YYYY)
        month_dates: list of date objects
        
    Returns:
        tuple: (actual_cumulative: list, last_enrollment_date: date or None)
    """
    # Get enrollment dates
    enrolled_qs = get_filtered_queryset(
        ENR_CASE, site_filter, filter_type
    ).filter(ENRDATE__isnull=False).values_list('ENRDATE', flat=True)
    
    enrollment_dates = list(enrolled_qs)
    last_enrollment_date = max(enrollment_dates) if enrollment_dates else None
    
    # Count by month
    enrollment_by_month = {}
    for enr_date in enrollment_dates:
        if enr_date:
            month_key = enr_date.strftime('%m/%Y')
            enrollment_by_month[month_key] = enrollment_by_month.get(month_key, 0) + 1
    
    # Build cumulative array
    actual_cumulative = []
    cumulative = 0
    has_started = False
    
    for i, month in enumerate(months):
        month_date = month_dates[i]
        month_count = enrollment_by_month.get(month, 0)
        
        # Cut off after last enrollment date
        if last_enrollment_date and month_date > last_enrollment_date:
            actual_cumulative.append(None)
        elif month_count > 0:
            has_started = True
            cumulative += month_count
            actual_cumulative.append(cumulative)
        elif has_started:
            actual_cumulative.append(cumulative)
        else:
            actual_cumulative.append(None)
    
    return actual_cumulative, last_enrollment_date


def _get_monthly_counts(model, site_filter, filter_type, date_field, start_date, end_date, months, extra_filters=None):
    """
    Get counts per month for a model.
    
    Args:
        model: Django model class
        site_filter: site code(s)
        filter_type: 'all' | 'single' | 'multiple'
        date_field: str - name of date field
        start_date: date
        end_date: date
        months: list of month labels
        extra_filters: dict - additional filter conditions
        
    Returns:
        list: Count per month
    """
    qs = get_filtered_queryset(model, site_filter, filter_type).filter(
        **{f'{date_field}__isnull': False},
        **{f'{date_field}__gte': start_date},
        **{f'{date_field}__lte': end_date},
    )
    
    if extra_filters:
        qs = qs.filter(**extra_filters)
    
    # Count by month
    counts_by_month = {}
    for record in qs.values(date_field):
        record_date = record[date_field]
        if record_date:
            month_key = record_date.strftime('%m/%Y')
            counts_by_month[month_key] = counts_by_month.get(month_key, 0) + 1
    
    return [counts_by_month.get(month, 0) for month in months]


# ============================================================================
# API ENDPOINTS (If needed for charts)
# ============================================================================

@require_GET
@login_required
def get_dashboard_stats_api(request):
    """
    API endpoint to refresh dashboard statistics
    
    Returns JSON with current counts
    
    Usage:
        GET /api/dashboard-stats/
        
    Response:
        {
            "success": true,
            "data": {
                "screening_patients": 150,
                "enrolled_patients": 120,
                "screening_contacts": 300,
                "enrolled_contacts": 250
            },
            "site_name": "003 - Hospital A",
            "timestamp": "2026-01-13T10:30:00"
        }
    """
    site_filter, filter_type = get_site_filter_params(request)
    
    try:
        # Get counts
        screening_patients = get_filtered_queryset(
            SCR_CASE, site_filter, filter_type
        ).count()
        
        enrolled_patients = get_filtered_queryset(
            SCR_CASE, site_filter, filter_type
        ).filter(
            UPPER16AGE=True,
            INFPRIOR2OR48HRSADMIT=True,
            ISOLATEDKPNFROMINFECTIONORBLOOD=True,
            KPNISOUNTREATEDSTABLE=False,
            CONSENTTOSTUDY=True,
            is_confirmed=True
        ).count()
        
        screening_contacts = get_filtered_queryset(
            SCR_CONTACT, site_filter, filter_type
        ).count()
        
        enrolled_contacts = get_filtered_queryset(
            ENR_CONTACT, site_filter, filter_type
        ).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'screening_patients': screening_patients,
                'enrolled_patients': enrolled_patients,
                'screening_contacts': screening_contacts,
                'enrolled_contacts': enrolled_contacts,
            },
            'site_name': _get_site_display_name(site_filter, filter_type),
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_GET
@login_required
def get_enrollment_chart_api(request):
    """
    API endpoint for enrollment chart data.
    
    Returns cumulative enrollment target and actual data for charting.
    """
    # Validate site access and get filter
    site_filter, filter_type, allowed_sites, error = get_site_filter_with_validation(request)
    if error:
        return error
    
    try:
        # Get configuration for current site
        if filter_type == 'all' or site_filter == 'all':
            config = SITE_CONFIG['all']
            site_target = config['target']
            site_start_date = config['start_date']
        elif filter_type == 'single':
            config = SITE_CONFIG.get(site_filter, {})
            site_target = config.get('target', 0)
            site_start_date = config.get('start_date', STUDY_START_DATE)
        elif filter_type == 'multiple':
            site_target = sum(SITE_CONFIG.get(s, {}).get('target', 0) for s in site_filter)
            site_start_date = min(
                SITE_CONFIG.get(s, {}).get('start_date', STUDY_START_DATE) 
                for s in site_filter
            )
        else:
            site_target = 0
            site_start_date = STUDY_START_DATE
        
        # Generate month labels
        months, month_dates = _generate_month_labels(STUDY_START_DATE, CHART_END_DATE)
        
        # Calculate target line
        target_cumulative = _calculate_target_cumulative(
            filter_type, site_filter, site_target, site_start_date, month_dates
        )
        
        # Get actual enrollment data
        actual_cumulative, last_enrollment_date = _calculate_actual_cumulative(
            site_filter, filter_type, months, month_dates
        )
        
        # Return data
        return JsonResponse({
            'success': True,
            'data': {
                'months': months,
                'target': target_cumulative,
                'actual': actual_cumulative,
                'site_target': site_target,
                'total_months': TOTAL_STUDY_MONTHS,
                'site_start_date': site_start_date.strftime('%d/%m/%Y'),
                'site_start_month': site_start_date.strftime('%m/%Y'),
                'chart_start_date': STUDY_START_DATE.strftime('%d/%m/%Y'),
                'chart_end_date': STUDY_END_DATE.strftime('%d/%m/%Y'),
                'last_enrollment_date': last_enrollment_date.strftime('%d/%m/%Y') if last_enrollment_date else None,
            },
            'allowed_sites': allowed_sites,
            'site_name': _get_site_display_name(site_filter, filter_type),
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Chart API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_GET
@login_required
def get_monthly_screening_enrollment_api(request):
    """API endpoint for monthly screening and enrollment statistics."""
    # Validate site access and get filter
    site_filter, filter_type, allowed_sites, error = get_site_filter_with_validation(request)
    if error:
        return error
    
    try:
        # Parse date range
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        start_date = (
            datetime.strptime(start_date_str, '%Y-%m-%d').date() 
            if start_date_str else STUDY_START_DATE
        )
        end_date = (
            datetime.strptime(end_date_str, '%Y-%m-%d').date() 
            if end_date_str else date.today()
        )
        
        # Generate month labels
        months, _ = _generate_month_labels(start_date, end_date.replace(day=1))
        
        # Get screening and enrollment data
        screening_data = _get_monthly_counts(
            SCR_CASE, site_filter, filter_type, 'SCREENINGFORMDATE', start_date, end_date, months
        )
        enrollment_data = _get_monthly_counts(
            SCR_CASE, site_filter, filter_type, 'SCREENINGFORMDATE', start_date, end_date, months,
            extra_filters={'is_confirmed': True}
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'months': months,
                'screening': screening_data,
                'enrollment': enrollment_data,
                'start_date': start_date.strftime('%d/%m/%Y'),
                'end_date': end_date.strftime('%d/%m/%Y'),
            },
            'site_name': _get_site_display_name(site_filter, filter_type),
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Monthly stats API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_GET
@login_required
def get_monthly_contact_stats_api(request):
    """API endpoint for monthly contact screening and enrollment statistics."""
    # Validate site access and get filter
    site_filter, filter_type, allowed_sites, error = get_site_filter_with_validation(request)
    if error:
        return error
    
    try:
        # Parse date range
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        start_date = (
            datetime.strptime(start_date_str, '%Y-%m-%d').date() 
            if start_date_str else STUDY_START_DATE
        )
        end_date = (
            datetime.strptime(end_date_str, '%Y-%m-%d').date() 
            if end_date_str else date.today()
        )
        
        # Generate month labels
        months, _ = _generate_month_labels(start_date, end_date.replace(day=1))
        
        # Get screening and enrollment data using helper
        screening_data = _get_monthly_counts(
            SCR_CONTACT, site_filter, filter_type, 'SCREENINGFORMDATE', start_date, end_date, months
        )
        enrollment_data = _get_monthly_counts(
            SCR_CONTACT, site_filter, filter_type, 'SCREENINGFORMDATE', start_date, end_date, months,
            extra_filters={'is_confirmed': True}
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'months': months,
                'screening': screening_data,
                'enrollment': enrollment_data,
                'start_date': start_date.strftime('%d/%m/%Y'),
                'end_date': end_date.strftime('%d/%m/%Y'),
            },
            'site_name': _get_site_display_name(site_filter, filter_type),
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Contact monthly stats API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_GET
@login_required
def get_sampling_followup_stats_api(request):
    """
    API endpoint for patient and contact sampling follow-up statistics.
    
    Query Parameters:
        site: Optional site code ('003', '020', '011', 'all')
    
    Returns:
        JSON with:
        - patient_data: Dict with sampling stats by visit
        - contact_data: Dict with sampling stats by visit
    
    Sample types counted:
    - Total sampling: STOOL + RECTSWAB + THROATSWAB (not blood)
    - Blood sampling: BLOOD only
    """
    # Validate site access and get filter
    site_filter, filter_type, allowed_sites, error = get_site_filter_with_validation(request)
    if error:
        return error
    
    def _get_visit_stats(samples_qs, visit_type):
        """Get sampling stats for a specific visit type."""
        visit_samples = samples_qs.filter(SAMPLE_TYPE=visit_type, SAMPLE=True)
        return {
            'total': visit_samples.count(),
            'blood': visit_samples.filter(BLOOD=True).count(),
        }
    
    try:
        # ===== PATIENT SAMPLING STATISTICS =====
        enrolled_patients = get_filtered_queryset(ENR_CASE, site_filter, filter_type).count()
        
        patient_samples_qs = SAM_CASE.objects.filter(
            USUBJID__in=get_filtered_queryset(ENR_CASE, site_filter, filter_type).values('USUBJID')
        )
        
        patient_stats = {
            'visit1': _get_visit_stats(patient_samples_qs, '1'),  # Day 1
            'visit2': _get_visit_stats(patient_samples_qs, '2'),  # Day 10
            'visit3': _get_visit_stats(patient_samples_qs, '3'),  # Day 28
            'visit4': _get_visit_stats(patient_samples_qs, '4'),  # Day 90
        }
        
        # ===== CONTACT SAMPLING STATISTICS =====
        enrolled_contacts = get_filtered_queryset(ENR_CONTACT, site_filter, filter_type).count()
        
        contact_samples_qs = SAM_CONTACT.objects.filter(
            USUBJID__in=get_filtered_queryset(ENR_CONTACT, site_filter, filter_type).values('USUBJID')
        )
        
        contact_stats = {
            'visit1': _get_visit_stats(contact_samples_qs, '1'),  # Day 1
            'visit2': {'total': None, 'blood': None},  # Not applicable for contacts
            'visit3': _get_visit_stats(contact_samples_qs, '3'),  # Day 28
            'visit4': _get_visit_stats(contact_samples_qs, '4'),  # Day 90
        }
        
        # ===== RETURN DATA =====
        return JsonResponse({
            'success': True,
            'data': {
                'patient': {
                    'enrolled': enrolled_patients,
                    'discharged': enrolled_patients,  # Placeholder
                    **patient_stats,
                },
                'contact': {
                    'enrolled': enrolled_contacts,
                    **contact_stats,
                },
            },
            'site_name': _get_site_display_name(site_filter, filter_type),
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Sampling followup API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_GET
@login_required
def get_kpneumoniae_isolation_stats_api(request):
    """
    API endpoint for K. pneumoniae isolation statistics from samples.
    
    Query Parameters:
        site: Optional site code ('003', '020', '011', 'all')
    
    Returns:
        JSON with isolation stats by site, subject type, and sample type
    
    Data Structure:
        - Clinical Kp: Patients with Klebsiella at enrollment/infection
        - Throat swab: Day 1, 10, 28, 90 (KLEBPNEU_3 positive / Total THROATSWAB)
        - Stool/Rectal: Day 1, 10, 28, 90 (KLEBPNEU_1 or KLEBPNEU_2 positive / Total STOOL or RECTSWAB)
    """
    from django.db.models import Q
    
    # Validate site access and get filter
    site_filter, filter_type, allowed_sites, error = get_site_filter_with_validation(request)
    if error:
        return error
    
    def _get_sample_stat(samples_qs, day, sample_type, positive_filter):
        """Get sample statistics for a specific day and sample type."""
        try:
            if sample_type == 'throat':
                samples = samples_qs.filter(SAMPLE_TYPE=day, THROATSWAB=True)
                total = samples.count()
                positive = samples.filter(KLEBPNEU_3=True).count()
            else:  # stool_rectal
                samples = samples_qs.filter(SAMPLE_TYPE=day).filter(Q(STOOL=True) | Q(RECTSWAB=True))
                total = samples.count()
                positive = samples.filter(Q(KLEBPNEU_1=True) | Q(KLEBPNEU_2=True)).count()
            return {
                'positive': positive,
                'total': total,
                'display': f"{positive}/{total}" if total > 0 else "-"
            }
        except Exception as e:
            logger.warning(f"Error getting {sample_type} samples day {day}: {e}")
            return {'positive': 0, 'total': 0, 'display': "-"}
    
    def _get_all_sample_stats(samples_qs):
        """Get all sample statistics (throat and stool_rectal) for all days."""
        throat = {f'day{day}': _get_sample_stat(samples_qs, day, 'throat', None) for day in ['1', '2', '3', '4']}
        stool_rectal = {f'day{day}': _get_sample_stat(samples_qs, day, 'stool_rectal', None) for day in ['1', '2', '3', '4']}
        return throat, stool_rectal
    
    try:
        # Get study's linked site codes from database
        study_site_codes = get_study_site_codes(request)
        site_names_map = get_site_names_from_db(request)
        
        # Determine which sites to query
        if filter_type == 'single':
            sites_to_query = [site_filter]
        elif filter_type == 'multiple':
            sites_to_query = [s for s in study_site_codes if s in site_filter]
        else:  # 'all'
            sites_to_query = list(study_site_codes)
        
        result_data = {}
        
        for site_code in sites_to_query:
            site_name = site_names_map.get(site_code, site_code)
            
            # ===== PATIENT DATA =====
            patients = ENR_CASE.objects.filter(USUBJID__SITEID=site_code)
            patient_count = patients.count()
            
            # Clinical Kp (patients with Klebsiella at enrollment/infection)
            clinical_kp = SCR_CASE.objects.filter(
                SITEID=site_code,
                is_confirmed=True,
                ISOLATEDKPNFROMINFECTIONORBLOOD=True
            ).count()
            
            # Get patient samples for this site
            try:
                patient_samples = SAM_CASE.objects.filter(USUBJID__USUBJID__SITEID=site_code)
            except Exception as e:
                logger.warning(f"Could not access SAM_CASE for site {site_code}: {e}")
                patient_samples = SAM_CASE.objects.none()
            
            # Get patient sample stats using helper
            patient_throat, patient_stool_rectal = _get_all_sample_stats(patient_samples)
            
            # ===== CONTACT DATA =====
            contacts = ENR_CONTACT.objects.filter(USUBJID__SITEID=site_code)
            contact_count = contacts.count()
            
            # Get contact samples for this site
            try:
                contact_samples = SAM_CONTACT.objects.filter(USUBJID__USUBJID__SITEID=site_code)
            except Exception as e:
                logger.warning(f"Could not access SAM_CONTACT for site {site_code}: {e}")
                contact_samples = SAM_CONTACT.objects.none()
            
            # Get contact sample stats using helper
            contact_throat, contact_stool_rectal = _get_all_sample_stats(contact_samples)
            
            # ===== BUILD SITE DATA =====
            result_data[site_code] = {
                'site_name': site_name,
                'patient': {
                    'count': patient_count,
                    'clinical_kp': clinical_kp,
                    'throat': patient_throat,
                    'stool_rectal': patient_stool_rectal,
                },
                'contact': {
                    'count': contact_count,
                    'throat': contact_throat,
                    'stool_rectal': contact_stool_rectal,
                },
                'complicated': {
                    'count': clinical_kp,  # Same as clinical_kp
                },
            }
        
        # ===== RETURN DATA =====
        return JsonResponse({
            'success': True,
            'data': result_data,
            'allowed_sites': allowed_sites,
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"K. pneumoniae isolation API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


