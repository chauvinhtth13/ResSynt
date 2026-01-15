# backends/api/studies/study_44en/urls.py
"""
Main URL Configuration for Study 44EN
"""

from django.urls import path, include

# Import views
from .views import views_audit
from .services import dashboard

# App name for namespacing
app_name = 'study_44en'

urlpatterns = [
    # ===== DASHBOARD & CHARTS =====
    path('dashboard/', dashboard.home_dashboard, name='home_dashboard'),
    
    # Dashboard API endpoints
    path('api/dashboard-stats/', 
         dashboard.get_dashboard_stats_api, 
         name='dashboard_stats_api'),
    
    path('api/ward-distribution/', 
         dashboard.get_ward_distribution_api, 
         name='ward_distribution_api'),
    
    # ===== HOUSEHOLD MODULE =====
    path('household/', include(('backends.api.studies.study_44en.views.household.urls', 'household'))),
    
    # ===== INDIVIDUAL MODULE =====
    path('individual/', include(('backends.api.studies.study_44en.views.individual.urls', 'individual'))),
    
    # ===== AUDIT LOG =====
    path('audit-logs/', views_audit.audit_log_list, name='audit_log_list'),
    path('audit-logs/<int:log_id>/', views_audit.audit_log_detail, name='audit_log_detail'),
]