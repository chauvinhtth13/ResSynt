from django.urls import path
from backends.api.studies.study_43en.services import dashboard

# App name for namespacing
app_name = 'study_43en'

urlpatterns = [
    # ============================================================================
    # MAIN DASHBOARD
    # ============================================================================
    path('dashboard/', 
         dashboard.home_dashboard, 
         name='home_dashboard'),
    
    # ============================================================================
    # API ENDPOINTS (Optional - for AJAX refresh)
    # ============================================================================
    path('api/dashboard-stats/', 
         dashboard.get_dashboard_stats_api, 
         name='dashboard_stats_api'),
]