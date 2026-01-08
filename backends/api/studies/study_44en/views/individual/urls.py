# backends/api/studies/study_44en/views/individual/urls.py
"""
Individual URL Configuration for Study 44EN
Following 43EN pattern with both 'edit' and 'update' aliases
"""

from django.urls import path

from .invidual_followup import views_individual_followup

from .invidual_exposure import views_individual_exposure

from .individual_case import views_individual_case
from .invidual_sample import (
    views_individual_sample
)

app_name = 'individual'

urlpatterns = [
    # ===== INDIVIDUAL CASE =====
    path('', views_individual_case.individual_list, name='list'),
    path('create/', views_individual_case.individual_create, name='create'),
    path('<str:subjectid>/', views_individual_case.individual_detail, name='detail'),
    
    # Use individual_update (new name) for both update and edit URLs
    path('<str:subjectid>/update/', views_individual_case.individual_update, name='update'),
    path('<str:subjectid>/edit/', views_individual_case.individual_update, name='edit'),  # Alias for compatibility
    
    # ===== INDIVIDUAL EXPOSURE =====
    path('<str:subjectid>/exposure-list/', views_individual_exposure.individual_exposure_list, name='exposure_list'),
    path('<str:subjectid>/exposure/', views_individual_exposure.individual_exposure, name='exposure'),  # Deprecated
    path('<str:subjectid>/exposure/create/', views_individual_exposure.individual_exposure_create, name='exposure_create'),
    path('<str:subjectid>/exposure/update/', views_individual_exposure.individual_exposure_update, name='exposure_update'),
    path('<str:subjectid>/exposure/view/', views_individual_exposure.individual_exposure_view, name='exposure_view'),
    
    # ===== INDIVIDUAL EXPOSURE 2 (EXP 2/3) - Vaccination & Hospitalization =====
    path('<str:subjectid>/exposure-2/create/', views_individual_exposure.individual_exposure_2_create, name='exposure_2_create'),
    path('<str:subjectid>/exposure-2/update/', views_individual_exposure.individual_exposure_2_update, name='exposure_2_update'),
    path('<str:subjectid>/exposure-2/view/', views_individual_exposure.individual_exposure_2_view, name='exposure_2_view'),
    
    # ===== INDIVIDUAL EXPOSURE 3 (EXP 3/3) - Food & Travel =====
    path('<str:subjectid>/exposure-3/create/', views_individual_exposure.individual_exposure_3_create, name='exposure_3_create'),
    path('<str:subjectid>/exposure-3/update/', views_individual_exposure.individual_exposure_3_update, name='exposure_3_update'),
    path('<str:subjectid>/exposure-3/view/', views_individual_exposure.individual_exposure_3_view, name='exposure_3_view'),
    
    # ===== INDIVIDUAL FOLLOW-UP =====
    path('<str:subjectid>/followup/', views_individual_followup.individual_followup_list, name='followup_list'),
    path('<str:subjectid>/followup/create/', views_individual_followup.individual_followup_create, name='followup_create'),
    path('<str:subjectid>/followup/<str:followup_id>/', views_individual_followup.individual_followup_detail, name='followup_detail'),
    path('<str:subjectid>/followup/<str:followup_id>/update/', views_individual_followup.individual_followup_update, name='followup_update'),
    path('<str:subjectid>/followup/<str:followup_id>/view/', views_individual_followup.individual_followup_view, name='followup_view'),
    
    # ===== INDIVIDUAL SAMPLE =====
    path('<str:subjectid>/sample/', views_individual_sample.individual_sample, name='sample'),
    path('<str:subjectid>/sample/create/', views_individual_sample.individual_sample_create, name='sample_create'),
    path('<str:subjectid>/sample/update/', views_individual_sample.individual_sample_update, name='sample_update'),
    path('<str:subjectid>/sample/view/', views_individual_sample.individual_sample_view, name='sample_view'),
]
