# backends/api/base/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('select-study/', views.select_study, name='select_study'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Include allauth URLs (đã có sẵn logout)
    path('accounts/', include('allauth.urls')),
]