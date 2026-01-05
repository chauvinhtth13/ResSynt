# backends/api/studies/study_44en/urls.py
"""
Main URL Configuration for Study 44EN
"""

from django.urls import path, include

# Import views
from .views import views_base, views_audit

# App name for namespacing
app_name = 'study_44en'

urlpatterns = [
    # ===== DASHBOARD =====
    path('dashboard/', views_base.dashboard, name='dashboard'),
    
    # ===== HOUSEHOLD MODULE =====
    path('household/', include(('backends.api.studies.study_44en.views.household.urls', 'household'))),
    
    # ===== INDIVIDUAL MODULE =====
    path('individual/', include(('backends.api.studies.study_44en.views.individual.urls', 'individual'))),
    
    # ===== AUDIT LOG =====
    path('audit-logs/', views_audit.audit_log_list, name='audit_log_list'),
    path('audit-logs/<int:log_id>/', views_audit.audit_log_detail, name='audit_log_detail'),
]