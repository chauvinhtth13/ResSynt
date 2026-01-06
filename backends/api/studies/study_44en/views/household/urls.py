# backends/api/studies/study_44en/views/household/urls.py
"""
Household URL Configuration for Study 44EN
Following 43EN pattern with separate CREATE/UPDATE/VIEW endpoints

UPDATED: Added separate CREATE/UPDATE/VIEW for exposure and food
"""

from django.urls import path

from .views_exposure import views_household_exposure
from . import (
    views_household_case,
    views_household_food,
)

app_name = 'household'

urlpatterns = [
    # ===== HOUSEHOLD CASE (Main) =====
    path('', views_household_case.household_list, name='list'),
    path('create/', views_household_case.household_create, name='create'),
    path('<str:hhid>/', views_household_case.household_detail, name='detail'),
    
    # Both 'edit' and 'update' point to same view (for template compatibility)
    path('<str:hhid>/update/', views_household_case.household_update, name='update'),
    path('<str:hhid>/edit/', views_household_case.household_update, name='edit'),  # Alias
    
    path('<str:hhid>/view/', views_household_case.household_view, name='view'),
    
    # ===== HOUSEHOLD EXPOSURE =====
    # Create new exposure data
    path('<str:hhid>/exposure/create/', 
         views_household_exposure.household_exposure_create, 
         name='exposure_create'),
    
    # Update existing exposure data
    path('<str:hhid>/exposure/update/', 
         views_household_exposure.household_exposure_update, 
         name='exposure_update'),
    
    # Both 'edit' and 'update' work (for template compatibility)
    path('<str:hhid>/exposure/edit/', 
         views_household_exposure.household_exposure_update, 
         name='exposure_edit'),  # Alias
    
    # View exposure data (read-only)
    path('<str:hhid>/exposure/view/', 
         views_household_exposure.household_exposure_view, 
         name='exposure_view'),
    
    # Legacy endpoint - smart redirect to create or update
    path('<str:hhid>/exposure/', 
         views_household_exposure.household_exposure, 
         name='exposure'),
    
    # ===== HOUSEHOLD FOOD =====
    # Create new food data
    path('<str:hhid>/food/create/', 
         views_household_food.household_food_create, 
         name='food_create'),
    
    # Update existing food data
    path('<str:hhid>/food/update/', 
         views_household_food.household_food_update, 
         name='food_update'),
    
    # Both 'edit' and 'update' work (for template compatibility)
    path('<str:hhid>/food/edit/', 
         views_household_food.household_food_update, 
         name='food_edit'),  # Alias
    
    # View food data (read-only)
    path('<str:hhid>/food/view/', 
         views_household_food.household_food_view, 
         name='food_view'),
    
    # Legacy endpoint - smart redirect to create or update
    path('<str:hhid>/food/', 
         views_household_food.household_food, 
         name='food'),
]