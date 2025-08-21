# apps/studies/urls.py
from django.urls import path
from .views import custom_study_view

app_name = 'studies'
urlpatterns = [
    path('<str:study_code>/custom-page/', custom_study_view, name='custom_page'),
]