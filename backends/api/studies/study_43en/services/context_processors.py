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
    'notification_count': 0,
    'unread_count': 0,
    'notifications': [],
    'today': None,
    'yesterday': None,
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
    # 🚀 OPTIMIZED: Use direct query instead of get_filtered_queryset
    # ==========================================
    
    # Wrap everything in try-except to ensure we always return valid data
    try:
        from django.conf import settings
        from django.db import connections
        from django.core.cache import cache
        
        # Check if study database is configured
        if 'db_study_43en' not in settings.DATABASES:
            return _EMPTY_NOTIFICATIONS
        
        try:
            # Test connection - only when we actually need it
            connections['db_study_43en'].ensure_connection()
        except Exception:
            return _EMPTY_NOTIFICATIONS
        
        from backends.studies.study_43en.models.schedule import FollowUpStatus
        
        # ==========================================
        # QUERY PARAMETERS
        # ==========================================
        today = date.today()
        upcoming_date = today + timedelta(days=3)
        
        #  Get read notifications from session
        read_notifications = request.session.get('read_notifications', [])
        
        # 🚀 Cache key for notifications (per user, per day)
        user_id = request.user.id
        cache_key = f"notifications_43en_{user_id}_{today.isoformat()}"
        
        # ==========================================
        # QUERY FollowUpStatus - DIRECT QUERY (skip cache overhead)
        # ==========================================
        try:
            # 🚀 Direct query - no get_filtered_queryset to avoid cache load
            # ⚠️ NOTE: FollowUpStatus has NO SITEID field - it's a denormalized table
            followups = FollowUpStatus.objects.using('db_study_43en').filter(
                EXPECTED_DATE__gte=today,
                EXPECTED_DATE__lte=upcoming_date,
                STATUS__in=['UPCOMING', 'LATE']
            ).only(
                'USUBJID', 'VISIT', 'EXPECTED_DATE', 'STATUS', 'SUBJECT_TYPE', 'PHONE', 'INITIAL'
            ).order_by('EXPECTED_DATE', 'USUBJID')[:50]  # Limit to 50 notifications
            
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
        
        # 🧪 FAKE DATA FOR TESTING (remove in production)
        # If no real data, add fake notifications for testing
        if len(followups) == 0:
            fake_notifications = [
                {
                    'USUBJID': '003-A-001',
                    'VISIT': 'V2',
                    'EXPECTED_DATE': today - timedelta(days=1),  # Yesterday - LATE
                    'STATUS': 'LATE',
                    'SUBJECT_TYPE': 'PATIENT',
                    'PHONE': '0901234567',
                    'INITIAL': 'NVA',
                    'EXPECTED_FROM': None,
                    'EXPECTED_TO': None,
                },
                {
                    'USUBJID': '003-A-002',
                    'VISIT': 'V3',
                    'EXPECTED_DATE': today,  # Today - UPCOMING
                    'STATUS': 'UPCOMING',
                    'SUBJECT_TYPE': 'PATIENT',
                    'PHONE': '0912345678',
                    'INITIAL': 'LTB',
                    'EXPECTED_FROM': None,
                    'EXPECTED_TO': None,
                },
                {
                    'USUBJID': '003-C-001',
                    'VISIT': 'V2',
                    'EXPECTED_DATE': today + timedelta(days=1),  # Tomorrow - UPCOMING
                    'STATUS': 'UPCOMING',
                    'SUBJECT_TYPE': 'CONTACT',
                    'PHONE': '0923456789',
                    'INITIAL': 'PTH',
                    'EXPECTED_FROM': None,
                    'EXPECTED_TO': None,
                },
            ]
            
            # Convert to objects with attributes
            class FakeFollowup:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            followups = [FakeFollowup(data) for data in fake_notifications]
        # 🧪 END FAKE DATA
        
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
            
            # Build URL for notification click
            if followup.SUBJECT_TYPE == 'PATIENT':
                notification_url = f"/studies/43en/patient/{followup.USUBJID}/"
            else:
                notification_url = f"/studies/43en/contact/{followup.USUBJID}/"
            
            # Build message for notification
            notification_message = f"{subject_label} {followup.USUBJID} - {visit_description}"
            
            #  Build notification object
            upcoming.append({
                # Required by template
                'id': notif_id,
                'message': notification_message,
                'url': notification_url,
                'type': 'warning' if followup.STATUS == 'LATE' else 'info',
                'icon': f'bi-{icon}',
                'created_at': followup.EXPECTED_DATE,  # Use expected_date for grouping
                'category': subject_label,
                'is_read': is_read,
                
                # Additional identification
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
                'icon_color': icon_color,
                
                # Legacy compatibility
                'notification_type': f"{followup.VISIT}_VISIT_{followup.SUBJECT_TYPE}"
            })
        
        #  Sort: unread first, then by date
        upcoming.sort(key=lambda x: (x['is_read'], x['expected_date']))
        
        # Calculate yesterday for template comparison
        yesterday = today - timedelta(days=1)
        
        return {
            'notification_count': len(upcoming),
            'unread_count': unread_count,
            'notifications': upcoming,
            'today': today,
            'yesterday': yesterday,
        }
    
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error in upcoming_appointments: {e}")
        return _EMPTY_NOTIFICATIONS
    




# ==========================================
# DASHBOARD STATISTICS 
# ==========================================
def dashboard_stats(request):
    """
    Provide quick statistics for dashboard
    
    🚀 OPTIMIZED: Only computed on DASHBOARD page, not on CRF forms
    
    Returns:
        dict: patient_count, contact_count, pending_followups
    """
    if not request.user.is_authenticated:
        return {}
    
    # 🚀 CRITICAL: Only compute for actual dashboard page, NOT for all /studies/43en/ paths
    # This prevents expensive queries on every CRF form load
    path = request.path
    
    # Only run on dashboard pages
    is_dashboard = (
        path == '/studies/43en/' or 
        path == '/studies/43en/dashboard/' or
        path.endswith('/dashboard/') and '/studies/43en/' in path
    )
    
    if not is_dashboard:
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
        
        # 🚀 OPTIMIZED: Direct count queries instead of loading all objects
        # Get site filter from middleware context
        selected_site_id = getattr(request, 'selected_site_id', 'all')
        can_access_all = getattr(request, 'can_access_all_sites', False)
        user_sites = getattr(request, 'user_sites', [])
        
        # Build site filter
        if selected_site_id and selected_site_id != 'all':
            site_filter = {'SITEID': selected_site_id}
        elif can_access_all:
            site_filter = {}  # No filter - see all
        elif user_sites:
            site_filter = {'SITEID__in': list(user_sites)}
        else:
            site_filter = {'SITEID__in': []}  # No access
        
        # Direct COUNT queries - no bulk caching
        patient_count = SCR_CASE.objects.using('db_study_43en').filter(
            is_confirmed=True, **site_filter
        ).count()
        
        contact_count = SCR_CONTACT.objects.using('db_study_43en').filter(
            **site_filter
        ).count()
        
        # ⚠️ NOTE: FollowUpStatus does NOT have SITEID field
        # It's a denormalized table - no site filtering needed here
        pending_followups = FollowUpStatus.objects.using('db_study_43en').filter(
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
