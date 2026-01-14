# backends/api/studies/study_44en/services/dashboard.py

from django.shortcuts import render

def home_dashboard(request):
    """Dashboard view for Study 44EN"""
    return render(request, 'studies/study_44en/home_dashboard.html', {
        'study_code': '44EN',
        'study_name': 'Study 44EN'
    })
