from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Count
from datetime import datetime
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

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

DB_ALIAS = 'db_study_43en'


# ============================================================================
# MAIN DASHBOARD VIEW
# ============================================================================

@login_required
def home_dashboard(request):
    """
    Main dashboard view - BACKEND ONLY
    
    Shows:
    - Screening patients count
    - Enrolled patients count
    - Screening contacts count
    - Enrolled contacts count
    
    All filtered by site from UnifiedTenancyMiddleware
    
    Args:
        request: HttpRequest with site context from middleware
        
    Returns:
        Rendered dashboard template with statistics
    """
    # Get site filter from middleware context
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"Dashboard loading - Site: {site_filter}, Type: {filter_type}")
    
    try:
        # ===== PATIENT STATISTICS =====
        # Count ALL screening patients
        screening_patients = get_filtered_queryset(
            SCR_CASE, 
            site_filter, 
            filter_type
        ).count()
        
        # Count ENROLLED patients (from SCR_CASE with eligibility criteria)
        enrolled_patients = get_filtered_queryset(
            SCR_CASE, 
            site_filter, 
            filter_type
        ).filter(
            UPPER16AGE=True,
            INFPRIOR2OR48HRSADMIT=True,
            ISOLATEDKPNFROMINFECTIONORBLOOD=True,
            KPNISOUNTREATEDSTABLE=False,
            CONSENTTOSTUDY=True,
            is_confirmed=True  # ✅ Must be confirmed
        ).count()
        
        logger.debug(f"Patients - Screening: {screening_patients}, Enrolled: {enrolled_patients}")
        
        # ===== CONTACT STATISTICS =====
        # Count ALL screening contacts
        screening_contacts = get_filtered_queryset(
            SCR_CONTACT,
            site_filter,
            filter_type
        ).count()
        
        # Count ENROLLED contacts (from ENR_CONTACT)
        enrolled_contacts = get_filtered_queryset(
            ENR_CONTACT,
            site_filter,
            filter_type
        ).count()
        
        logger.debug(f"Contacts - Screening: {screening_contacts}, Enrolled: {enrolled_contacts}")
        
        # ===== SITE NAME GENERATION =====
        site_name = _get_site_display_name(site_filter, filter_type)
        
        # ===== BUILD CONTEXT =====
        context = {
            # Study metadata
            'study': getattr(request, 'study', None),
            'study_code': '43en',
            'study_folder': 'studies/study_43en',
            'study_name': "Klebsiella pneumoniae Epidemiology Study",
            
            # Site information
            'site_name': site_name,
            'site_filter': site_filter,
            'filter_type': filter_type,
            
            # Statistics
            'screening_patients': screening_patients,
            'enrolled_patients': enrolled_patients,
            'screening_contacts': screening_contacts,
            'enrolled_contacts': enrolled_contacts,
            
            # Metadata
            'today': datetime.now(),
        }
        
        logger.info(
            f"Dashboard loaded successfully - "
            f"Patients: {screening_patients}/{enrolled_patients}, "
            f"Contacts: {screening_contacts}/{enrolled_contacts}"
        )
        
        return render(request, 'studies/study_43en/home_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        
        # Return error context
        return render(request, 'studies/study_43en/home_dashboard.html', {
            'error': str(e),
            'today': datetime.now(),
            'study_folder': 'studies/study_43en',
            'study_code': '43en',
        })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_site_display_name(site_filter, filter_type):
    """
    Generate human-readable site name for display
    
    Args:
        site_filter: 'all' | str | list
        filter_type: 'all' | 'single' | 'multiple'
        
    Returns:
        str: Display name (e.g., "All Sites", "003 - Site Name", "003, 011 (+2 more)")
    """
    if filter_type == 'all' or site_filter == 'all':
        return "All Sites"
    
    try:
        from backends.tenancy.models import Site
        
        if filter_type == 'single':
            # Single site
            site = Site.objects.get(code=site_filter)
            return f"{site.code} - {site.name}"
            
        elif filter_type == 'multiple':
            # Multiple sites
            sites = Site.objects.filter(code__in=site_filter)
            site_count = sites.count()
            
            if site_count == 0:
                return "No Sites"
            elif site_count == 1:
                site = sites.first()
                return f"{site.code} - {site.name}"
            else:
                # Show first 3 sites
                site_codes = [s.code for s in sites[:3]]
                site_names = ', '.join(site_codes)
                
                if site_count > 3:
                    return f"{site_names} (+{site_count - 3} more)"
                else:
                    return site_names
                    
    except Exception as e:
        logger.warning(f"Could not fetch site name: {e}")
        
        # Fallback
        if filter_type == 'single':
            return f"Site {site_filter}"
        elif filter_type == 'multiple' and site_filter:
            return f"{len(site_filter)} Sites"
        else:
            return "Unknown Site"
    
    return "All Sites"


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
    API endpoint for enrollment chart data
    
    Query Parameters:
        site: Optional site code ('003', '020', '011') to override user's site filter
    
    Returns:
        JSON with:
        - months: List of month labels (MM/YYYY format)
        - target: Target enrollment per month (cumulative) with stepped increase
        - actual: Actual enrollment per month (cumulative, null after last enrollment)
        - site_target: Total target for current site filter
    
    Target Logic:
        - All Sites: 15 patients/month (07/2024-06/2025), then adjust to reach 750 by 04/2027
        - Site 003: Starts 07/2024
        - Site 020: Starts 10/2025
        - Site 011: Starts 11/2025
    
    Usage:
        GET /api/enrollment-chart/
        GET /api/enrollment-chart/?site=003
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    # Check if site parameter is provided
    site_param = request.GET.get('site', None)
    
    if site_param and site_param != 'all':
        # Override with provided site
        site_filter = site_param
        filter_type = 'single'
        logger.info(f"Chart API: Using site from parameter: {site_param}")
    else:
        # Use default site filter from middleware
        site_filter, filter_type = get_site_filter_params(request)
        logger.info(f"Chart API: Using site from middleware: {site_filter}, type: {filter_type}")
    
    try:
        # ===== DEFINE TARGETS AND START DATES =====
        SITE_CONFIG = {
            'all': {
                'target': 750,
                'start_date': date(2024, 7, 1),
            },
            '003': {
                'target': 200,
                'start_date': date(2024, 7, 1),    # 01/07/2024
            },
            '020': {
                'target': 150,
                'start_date': date(2025, 10, 13),  # 13/10/2025
            },
            '011': {
                'target': 400,
                'start_date': date(2025, 11, 5),   # 05/11/2025
            },
        }
        
        # Get configuration for current site
        if filter_type == 'all' or site_filter == 'all':
            site_target = SITE_CONFIG['all']['target']
            site_start_date = SITE_CONFIG['all']['start_date']
        elif filter_type == 'single':
            config = SITE_CONFIG.get(site_filter, {})
            site_target = config.get('target', 0)
            site_start_date = config.get('start_date', date(2024, 7, 1))
        elif filter_type == 'multiple':
            # For multiple sites: earliest start date, sum of targets
            site_target = sum(SITE_CONFIG.get(site, {}).get('target', 0) for site in site_filter)
            site_start_date = min(
                SITE_CONFIG.get(site, {}).get('start_date', date(2024, 7, 1)) 
                for site in site_filter
            )
        else:
            site_target = 0
            site_start_date = date(2024, 7, 1)
        
        # ===== STUDY PERIOD =====
        chart_start_date = date(2024, 7, 1)   # Chart always starts from 07/2024
        end_date = date(2027, 4, 30)          # 30/04/2027
        
        # Calculate total months (07/2024 to 04/2027 = 34 months)
        # 2024: 6 months (Jul-Dec)
        # 2025: 12 months
        # 2026: 12 months  
        # 2027: 4 months (Jan-Apr)
        # Total: 34 months
        total_months = ((end_date.year - chart_start_date.year) * 12 + 
                       (end_date.month - chart_start_date.month) + 1)
        
        # ===== GENERATE MONTH LABELS =====
        months = []
        month_dates = []  # Keep date objects for calculations
        current_date = chart_start_date
        
        while current_date <= end_date:
            months.append(current_date.strftime('%m/%Y'))
            month_dates.append(current_date)
            current_date += relativedelta(months=1)
        
        logger.info(f"Total months calculated: {len(months)} (should be 34)")
        
        # ===== CALCULATE TARGET LINE (STEPPED TO REACH EXACT 750) =====
        # Phase 1 (07/2024-06/2025): 15/month for all sites
        # Phase 2 (07/2025-04/2027): Adjust to reach exactly 750 by 04/2027
        
        phase_1_end = date(2025, 6, 30)  # End of 15/month phase
        phase_1_months = 12  # Jul 2024 - Jun 2025
        phase_2_months = total_months - phase_1_months  # Remaining months
        
        if filter_type == 'all' or site_filter == 'all':
            # All sites
            phase_1_total = phase_1_months * 15  # 12 * 15 = 180
            phase_2_needed = site_target - phase_1_total  # 750 - 180 = 570
            phase_2_monthly = phase_2_needed / phase_2_months  # 570 / 22 = 25.9
        else:
            # Individual sites: proportional
            proportion = site_target / 750.0
            phase_1_total = phase_1_months * 15 * proportion
            phase_2_needed = site_target - phase_1_total
            phase_2_monthly = phase_2_needed / phase_2_months
        
        logger.info(f"Phase 1: {phase_1_months} months, Phase 2: {phase_2_months} months")
        logger.info(f"Phase 2 monthly: {phase_2_monthly:.2f} to reach {site_target}")
        
        target_cumulative = []
        cumulative_target = 0.0
        
        for month_date in month_dates:
            # Only accumulate if site has started
            if month_date >= site_start_date:
                # Determine step based on phase
                if month_date <= phase_1_end:
                    if filter_type == 'all' or site_filter == 'all':
                        monthly_step = 15
                    else:
                        monthly_step = 15 * proportion
                else:
                    monthly_step = phase_2_monthly
                
                cumulative_target += monthly_step
            
            target_cumulative.append(round(cumulative_target, 1))
        
        # Ensure last value is exactly the target
        if target_cumulative and cumulative_target > 0:
            target_cumulative[-1] = site_target
        
        # ===== GET ACTUAL ENROLLMENT DATA =====
        enrolled_qs = get_filtered_queryset(
            ENR_CASE, site_filter, filter_type
        ).filter(
            ENRDATE__isnull=False
        ).values('ENRDATE').order_by('ENRDATE')
        
        # Find last enrollment date
        enrollment_dates = [record['ENRDATE'] for record in enrolled_qs if record['ENRDATE']]
        last_enrollment_date = max(enrollment_dates) if enrollment_dates else None
        
        logger.info(f"Last enrollment date: {last_enrollment_date}")
        
        # Count enrollments by month
        enrollment_by_month = {}
        for enr_date in enrollment_dates:
            month_key = enr_date.strftime('%m/%Y')
            enrollment_by_month[month_key] = enrollment_by_month.get(month_key, 0) + 1
        
        # ===== CALCULATE ACTUAL CUMULATIVE WITH CUTOFF =====
        actual_cumulative = []
        cumulative_count = 0
        has_started = False
        cutoff_reached = False
        
        for i, month in enumerate(months):
            month_date = month_dates[i]
            month_count = enrollment_by_month.get(month, 0)
            
            # Check if we've passed last enrollment date
            if last_enrollment_date and month_date > last_enrollment_date:
                cutoff_reached = True
            
            if cutoff_reached:
                # After last enrollment, use null (cut the line)
                actual_cumulative.append(None)
            elif month_count > 0:
                has_started = True
                cumulative_count += month_count
                actual_cumulative.append(cumulative_count)
            elif has_started:
                # After first enrollment but no new enrollments this month
                actual_cumulative.append(cumulative_count)
            else:
                # Before first enrollment
                actual_cumulative.append(None)
        
        # ===== RETURN DATA =====
        return JsonResponse({
            'success': True,
            'data': {
                'months': months,
                'target': target_cumulative,
                'actual': actual_cumulative,
                'site_target': site_target,
                'total_months': total_months,
                'site_start_date': site_start_date.strftime('%d/%m/%Y'),
                'last_enrollment_date': last_enrollment_date.strftime('%d/%m/%Y') if last_enrollment_date else None,
            },
            'site_name': _get_site_display_name(site_filter, filter_type),
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Chart API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)