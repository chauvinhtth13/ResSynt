# backends/api/base/urls.py
from django.urls import path, include
from . import views
from .health import (
    HealthCheckView,
    DetailedHealthCheckView,
    ReadinessCheckView,
    LivenessCheckView,
)

urlpatterns = [
    path('select-study/', views.select_study, name='select_study'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Include allauth URLs (đã có sẵn logout)
    path('accounts/', include('allauth.urls')),
    
    # Health check endpoints
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('health/detailed/', DetailedHealthCheckView.as_view(), name='health_check_detailed'),
    path('health/ready/', ReadinessCheckView.as_view(), name='health_check_ready'),
    path('health/live/', LivenessCheckView.as_view(), name='health_check_live'),
]