# backends/studies/study_44en/urls.py
"""
Study 44EN URL Configuration - Following 43EN pattern
"""

from django.urls import path, include

# Import views from API layer
from backends.api.studies.study_44en.views import views_dashboard
from backends.api.studies.study_44en.views.household.views_food import (
    views_household_food,
)
from backends.api.studies.study_44en.views.household.views_case import views_household_case
from backends.api.studies.study_44en.views.household.views_exposure import views_household_exposure
from backends.api.studies.study_44en.views.individual import (
    views_individual_exposure,
    views_individual_followup,
    views_individual_sample,
)
from backends.api.studies.study_44en.views.individual.individual_case import views_individual_case

# App name for namespacing
app_name = 'study_44en'

urlpatterns = [
    # ===== DASHBOARD =====
    path('dashboard/', views_dashboard.dashboard_44en, name='home_dashboard'),
    
    # ===== HOUSEHOLD URLS (namespace: study_44en:household:xxx) =====
    path('household/', include('backends.api.studies.study_44en.views.household.urls', namespace='household')),
    
    # ===== INDIVIDUAL URLS (namespace: study_44en:individual:xxx) =====
    path('individual/', include('backends.api.studies.study_44en.views.individual.urls', namespace='individual')),
]
