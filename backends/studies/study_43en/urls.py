from django.urls import path
from backends.api.studies.study_43en.services import dashboard
from backends.api.studies.study_43en.views import views_report

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
    
    # ============================================================================
    # REPORT EXPORT
    # ============================================================================
    path('report/export/', 
         views_report.report_export_view, 
         name='report_export'),
]
