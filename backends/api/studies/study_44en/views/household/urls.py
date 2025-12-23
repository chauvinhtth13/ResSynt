# backends/api/studies/study_44en/views/household/urls.py
"""
Household URL Configuration for Study 44EN
Following 43EN pattern with both 'edit' and 'update' aliases
"""

from django.urls import path
from . import views_household_case, views_household_exposure, views_household_food

app_name = 'household'

urlpatterns = [
    # ===== HOUSEHOLD CASE =====
    path('', views_household_case.household_list, name='list'),
    path('create/', views_household_case.household_create, name='create'),
    path('<str:hhid>/', views_household_case.household_detail, name='detail'),
    
    # Both 'edit' and 'update' point to same view (for template compatibility)
    path('<str:hhid>/update/', views_household_case.household_update, name='update'),
    path('<str:hhid>/edit/', views_household_case.household_update, name='edit'),  # Alias
    
    path('<str:hhid>/view/', views_household_case.household_view, name='view'),
    
    # ===== HOUSEHOLD EXPOSURE (OLD VIEW - needs refactoring) =====
    path('<str:hhid>/exposure/', views_household_exposure.household_exposure, name='exposure'),
    
    # ===== HOUSEHOLD FOOD (OLD VIEW - needs refactoring) =====
    path('<str:hhid>/food/', views_household_food.household_food, name='food'),
]
