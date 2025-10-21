# backend/api/base/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.custom_login, name='login'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Study selection
    path('select-study/', views.select_study, name='select_study'),
    
    # Main dashboard (redirect to study-specific)
    # path('dashboard/', views.dashboard, name='dashboard'),
    path("password-reset/", views.custom_login, name="password_reset")
]