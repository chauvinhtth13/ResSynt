# backend/api/studies/study_43en/urls.py

from django.urls import path, include
from django.conf import settings

# Import views từ folder views/
from .views import views_scr_case

# App name for namespacing
app_name = 'study_43en'

urlpatterns = [
    # ===== SCREENING CASE =====
    path('screening/', views_scr_case.screening_case_list, name='screening_case_list'),
    path('screening/create/', views_scr_case.screening_case_create, name='screening_case_create'),
    path('screening/<str:SCRID>/view/', views_scr_case.screening_case_view, name='screening_case_view'),
    path('screening/<str:usubjid>/update/', views_scr_case.screening_case_update, name='screening_case_update'),
]

