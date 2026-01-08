# backends/api/studies/study_44en/views/urls_dashboard.py

"""
Dashboard URL Configuration for Study 44EN
"""

from django.urls import path
from .views_dashboard import dashboard_44en

urlpatterns = [
    path('dashboard/', dashboard_44en, name='dashboard'),
]
