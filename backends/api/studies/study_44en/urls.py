# backends/api/studies/study_44en/urls.py
"""
Main URL Configuration for Study 44EN
"""

from django.urls import path, include

# Import views
from .views import views_base

# App name for namespacing
app_name = 'study_44en'

urlpatterns = [
    # ===== DASHBOARD =====
    path('dashboard/', views_base.dashboard, name='dashboard'),
    
    # ===== HOUSEHOLD MODULE =====
    path('household/', include(('backends.api.studies.study_44en.views.household.urls', 'household'))),
    
    # ===== INDIVIDUAL MODULE =====
    path('individual/', include(('backends.api.studies.study_44en.views.individual.urls', 'individual'))),
]