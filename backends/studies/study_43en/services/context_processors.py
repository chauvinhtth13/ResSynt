# backends/studies/study_43en/services/context_processors.py
"""
Context processors for Study 43EN
Provides global context variables for all templates
"""
from datetime import date, timedelta
from django.db.models import Q


# ==========================================
# SITE FILTER CONTEXT
# ==========================================
def site_filter_context(request):
    """
    Provide site selection information for templates
    
    Returns:
        dict: available_sites, selected_site_id
    """
    available_sites = [
        {'id': '003', 'name': 'Site 003 - HTD'},
        {'id': '011', 'name': 'Site 011 - CRH'},
        {'id': '020', 'name': 'Site 020 - NHTD'},
    ]
    
    selected_site_id = request.session.get('selected_site_id', 'all')
    
    return {
        'available_sites': available_sites,
        'selected_site_id': selected_site_id
    }


# ==========================================
# EMPTY CONTEXT (for early returns)
# ==========================================
_EMPTY_NOTIFICATIONS = {
    'upcoming_count': 0,
    'unread_count': 0,
    'upcoming_patients': []
}

# Paths that don't need notifications (performance optimization)
_SKIP_NOTIFICATION_PATHS = (
    '/accounts/',
    '/admin/',
    '/static/',
    '/media/',
    '/i18n/',
    '/health/',
    '/select-study/',
    '/password-reset/',
)


# ==========================================
# UPCOMING APPOINTMENTS (NOTIFICATIONS)
# ==========================================
def upcoming_appointments(request):
    """
    Provide upcoming appointments for notification bell WITH PROPER SITE FILTERING
    
    PERFORMANCE OPTIMIZED:
    - Early return for anonymous users (before any DB operations)
    - Skip non-study paths (login, admin, static, etc.)
    - Only query database when absolutely necessary
    
    Features:
    - Uses FollowUpStatus (single source of truth)
    - Tracks read/unread status via session
    - Includes PHONE for contact
    - Shows STATUS (LATE/UPCOMING)
    - Uses get_site_filter_params() for correct site filtering
    
    Returns:
        dict: {
            'upcoming_count': Total notifications,
            'unread_count': Unread notifications,
            'upcoming_patients': List of notification objects
        }
    """
    # ==========================================
    # FAST PATH: Skip expensive operations for non-study pages
    # ==========================================
    
    # 1. Anonymous users - return immediately (no DB check needed)
    if not request.user.is_authenticated:
        return _EMPTY_NOTIFICATIONS
    
    # 2. Skip non-study paths (login, admin, static files, etc.)
    path = request.path
    if any(path.startswith(skip_path) for skip_path in _SKIP_NOTIFICATION_PATHS):
        return _EMPTY_NOTIFICATIONS
    
    # 3. Only process for study-related paths
    if not path.startswith('/studies/'):
        # Also allow dashboard which needs notifications
        if '/dashboard' not in path:
            return _EMPTY_NOTIFICATIONS
    
    # ==========================================
    # SLOW PATH: Database operations (only for study pages)
    # ==========================================
    from django.conf import settings
    from django.db import connections
    
    # Check if study database is configured
    if 'db_study_43en' not in settings.DATABASES:
        return _EMPTY_NOTIFICATIONS
    
    try:
        # Test connection - only when we actually need it
        connections['db_study_43en'].ensure_connection()
    except Exception:
        return _EMPTY_NOTIFICATIONS
    
    from backends.studies.study_43en.models.schedule import FollowUpStatus
    # FIX: Import from correct location (study utils, not audit_log utils)
    from backends.studies.study_43en.utils.site_utils import get_site_filter_params, get_filtered_queryset
    
    # ==========================================
    # QUERY PARAMETERS
    # ==========================================
    today = date.today()
    upcoming_date = today + timedelta(days=3)
    
    #  Use proper site filtering from middleware
    site_filter, filter_type = get_site_filter_params(request)
    
    #  Get read notifications from session
    read_notifications = request.session.get('read_notifications', [])
    
    # ==========================================
    # QUERY FollowUpStatus WITH SITE FILTERING
    # ==========================================
    try:
        #  Use get_filtered_queryset to match dashboard logic
        followups = get_filtered_queryset(FollowUpStatus, site_filter, filter_type)
        
        # Filter: upcoming within 3 days, not completed
        followups = followups.filter(
            EXPECTED_DATE__gte=today,
            EXPECTED_DATE__lte=upcoming_date,
            STATUS__in=['UPCOMING', 'LATE']  # Exclude COMPLETED and MISSED
        ).order_by('EXPECTED_DATE', 'USUBJID')
        
    except Exception as e:
        # Fallback if query fails
        import logging
        logging.getLogger(__name__).warning(f"Error querying FollowUpStatus: {e}")
        return _EMPTY_NOTIFICATIONS
    
    # ==========================================
    # BUILD NOTIFICATION LIST
    # ==========================================
    upcoming = []
    unread_count = 0
    
    for followup in followups:
        #  Create unique notification ID
        notif_id = f"{followup.USUBJID}_{followup.VISIT}_{followup.EXPECTED_DATE.strftime('%Y%m%d')}"
        
        #  Check read status
        is_read = notif_id in read_notifications
        
        if not is_read:
            unread_count += 1
        
        #  Determine visit label and icon
        if followup.SUBJECT_TYPE == 'PATIENT':
            subject_label = 'Bệnh nhân'
            if followup.VISIT == 'V2':
                visit_label = 'V2 (Day 7)'
                visit_description = 'Lấy mẫu ngày 7'
                icon = 'clipboard-pulse'
                icon_color = 'info'
            elif followup.VISIT == 'V3':
                visit_label = 'V3 (Day 28)'
                visit_description = 'Theo dõi 28 ngày'
                icon = 'calendar-check'
                icon_color = 'warning'
            else:  # V4
                visit_label = 'V4 (Day 90)'
                visit_description = 'Theo dõi 90 ngày'
                icon = 'calendar-event'
                icon_color = 'success'
        else:  # CONTACT
            subject_label = 'Người tiếp xúc'
            if followup.VISIT == 'V2':
                visit_label = 'V2 (Day 28)'
                visit_description = 'Theo dõi 28 ngày'
                icon = 'calendar-check'
                icon_color = 'warning'
            else:  # V3
                visit_label = 'V3 (Day 90)'
                visit_description = 'Theo dõi 90 ngày'
                icon = 'calendar-event'
                icon_color = 'success'
        
        #  Build notification object
        upcoming.append({
            # Identification
            'notif_id': notif_id,
            'usubjid': followup.USUBJID,
            'patient_name': followup.INITIAL or 'N/A',
            
            # Visit info
            'visit': followup.VISIT,
            'visit_label': visit_label,
            'visit_type': f"{visit_label} - {subject_label}",
            'visit_description': visit_description,
            
            # Subject type
            'subject_type': followup.SUBJECT_TYPE,
            'subject_label': subject_label,
            
            # Dates
            'expected_date': followup.EXPECTED_DATE,
            'expected_from': followup.EXPECTED_FROM,
            'expected_to': followup.EXPECTED_TO,
            
            # Status
            'status': followup.STATUS,
            'status_label': followup.get_STATUS_display() if hasattr(followup, 'get_STATUS_display') else followup.STATUS,
            'is_late': followup.STATUS == 'LATE',
            
            # Contact
            'phone': followup.PHONE,
            'has_phone': bool(followup.PHONE),
            
            # UI
            'icon': icon,
            'icon_color': icon_color,
            'is_read': is_read,
            
            # Legacy compatibility
            'notification_type': f"{followup.VISIT}_VISIT_{followup.SUBJECT_TYPE}"
        })
    
    #  Sort: unread first, then by date
    upcoming.sort(key=lambda x: (x['is_read'], x['expected_date']))
    
    return {
        'upcoming_count': len(upcoming),
        'unread_count': unread_count,
        'upcoming_patients': upcoming,
        'site_filtered_notifications': True,
        'notification_site_filter': site_filter,
        'notification_filter_type': filter_type
    }


# ==========================================
# STUDY CONTEXT
# ==========================================
def study_context(request):
    """
    Add study-specific context variables to all templates
    
    Returns:
        dict: study_folder, study_code, study_name
    """
    return {
        'study_folder': 'studies/study_43en',
        'study_code': '43EN',
        'study_name': 'Clinical Trial 43EN',
    }


# ==========================================
# DASHBOARD STATISTICS (Optional)
# ==========================================
def dashboard_stats(request):
    """
    Provide quick statistics for dashboard
    Only computed if user is authenticated and on dashboard page
    
    Returns:
        dict: patient_count, contact_count, pending_followups
    """
    if not request.user.is_authenticated:
        return {}
    
    # Only compute for dashboard page to avoid overhead
    if not request.path.startswith('/studies/43en/'):
        return {}
    
    # Check if study database is configured
    from django.conf import settings
    from django.db import connections
    
    if 'db_study_43en' not in settings.DATABASES:
        return {}
    
    try:
        # Test connection
        connections['db_study_43en'].ensure_connection()
    except Exception:
        return {}
    
    try:
        from backends.studies.study_43en.models.patient import SCR_CASE
        from backends.studies.study_43en.models.contact import SCR_CONTACT
        from backends.studies.study_43en.models.schedule import FollowUpStatus
        from backends.studies.study_43en.utils.site_utils import get_site_filter_params, get_filtered_queryset
        
        #  Use proper site filtering from middleware
        site_filter, filter_type = get_site_filter_params(request)
        
        # Patient count with site filtering
        patient_count = get_filtered_queryset(SCR_CASE, site_filter, filter_type).filter(is_confirmed=True).count()
        contact_count = get_filtered_queryset(SCR_CONTACT, site_filter, filter_type).count()
        pending_followups = get_filtered_queryset(FollowUpStatus, site_filter, filter_type).filter(
            STATUS__in=['UPCOMING', 'LATE']
        ).count()
        
        return {
            'dashboard_patient_count': patient_count,
            'dashboard_contact_count': contact_count,
            'dashboard_pending_followups': pending_followups,
        }
    
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error computing dashboard stats: {e}")
        return {}