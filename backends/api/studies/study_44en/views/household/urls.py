# backends/api/studies/study_44en/views/household/urls.py

"""
Household URL Configuration for Study 44EN
"""

from django.urls import path
from . import views_household_case, views_household_exposure, views_household_food

app_name = 'household'

urlpatterns = [
    # Household CRUD
    path('', views_household_case.household_list, name='list'),
    path('create/', views_household_case.household_create, name='create'),
    path('<str:hhid>/', views_household_case.household_detail, name='detail'),
    path('<str:hhid>/edit/', views_household_case.household_edit, name='edit'),
    
    # Household Exposure
    path('<str:hhid>/exposure/', views_household_exposure.household_exposure, name='exposure'),
    
    # Household Food
    path('<str:hhid>/food/', views_household_food.household_food, name='food'),
]
