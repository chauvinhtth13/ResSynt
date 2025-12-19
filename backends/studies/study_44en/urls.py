# backend/studies/study_44en/urls.py

from django.urls import path
from backends.api.studies.study_44en.services import dashboard

# App name for namespacing
app_name = 'study_44en'

urlpatterns = [
    # Dashboard views will be added here
    path('dashboard/', 
         dashboard.home_dashboard, 
         name='home_dashboard'),
]
