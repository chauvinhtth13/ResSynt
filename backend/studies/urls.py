
# backend/studies/urls.py
"""
URL configuration for study views
"""
from django.urls import path
from . import views

app_name = 'studies'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.study_dashboard, name='dashboard'),
    
    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<str:patient_id>/', views.patient_detail, name='patient_detail'),
    
    # Data Export
    path('export/', views.data_export, name='data_export'),
]