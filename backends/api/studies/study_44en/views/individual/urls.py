# backends/api/studies/study_44en/views/individual/urls.py

"""
Individual URL Configuration for Study 44EN
"""

from django.urls import path
from . import (
    views_individual_case, views_individual_exposure,
    views_individual_followup, views_individual_sample
)

app_name = 'individual'

urlpatterns = [
    # Individual CRUD
    path('', views_individual_case.individual_list, name='list'),
    path('create/', views_individual_case.individual_create, name='create'),
    path('<str:subjectid>/', views_individual_case.individual_detail, name='detail'),
    path('<str:subjectid>/edit/', views_individual_case.individual_edit, name='edit'),
    
    # Individual Exposure
    path('<str:subjectid>/exposure/', views_individual_exposure.individual_exposure, name='exposure'),
    
    # Individual Follow-up
    path('<str:subjectid>/followup/', views_individual_followup.individual_followup_list, name='followup_list'),
    path('<str:subjectid>/followup/create/', views_individual_followup.individual_followup_create, name='followup_create'),
    path('<str:subjectid>/followup/<int:followup_id>/', views_individual_followup.individual_followup_detail, name='followup_detail'),
    
    # Individual Sample
    path('<str:subjectid>/sample/', views_individual_sample.individual_sample, name='sample'),
]
