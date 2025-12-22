# backends/api/studies/study_44en/urls.py

"""
URL Configuration for Study 44EN
"""

from django.urls import path, include
from django.views.generic import RedirectView

app_name = 'study_44en'

urlpatterns = [
    # Dashboard
    path('', include('backends.api.studies.study_44en.views.urls_dashboard')),
    
    # Household views
    path('household/', include('backends.api.studies.study_44en.views.household.urls')),
    
    # Individual views
    path('individual/', include('backends.api.studies.study_44en.views.individual.urls')),
]
