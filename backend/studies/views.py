# backend/studies/views.py
"""
Generic views for study data access
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.http import JsonResponse
from backend.tenancy.db_router import get_current_db
from backend.studies.utils import StudyModelLoader, study_database_context, get_study_statistics
import logging

logger = logging.getLogger(__name__)


@login_required
def study_dashboard(request):
    """Dashboard showing study statistics"""
    study = getattr(request, 'study', None)
    
    if not study:
        messages.error(request, 'No study selected')
        return redirect('select_study')
    
    # Get statistics
    stats = get_study_statistics(study)
    
    # Get recent activities (example)
    recent_activities = []
    
    with study_database_context(study):
        # Get Patient model for this study
        Patient = StudyModelLoader.get_model(study.code, 'Patient')
        if Patient:
            recent_patients = Patient.objects.using(study.db_name).order_by('-created_at')[:5]
            for patient in recent_patients:
                recent_activities.append({
                    'type': 'patient',
                    'description': f'New patient enrolled: {patient.patient_id}',
                    'date': patient.created_at
                })
        
        # Get Visit model
        Visit = StudyModelLoader.get_model(study.code, 'Visit')
        if Visit:
            recent_visits = Visit.objects.using(study.db_name).order_by('-created_at')[:5]
            for visit in recent_visits:
                recent_activities.append({
                    'type': 'visit',
                    'description': f'Visit completed: {visit.patient.patient_id} - {visit.visit_type}',
                    'date': visit.created_at
                })
    
    # Sort activities by date
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'study': study,
        'stats': stats,
        'recent_activities': recent_activities[:10],
        'current_db': get_current_db(),
    }
    
    return render(request, 'studies/dashboard.html', context)


@login_required
def patient_list(request):
    """List all patients in the current study"""
    study = getattr(request, 'study', None)
    
    if not study:
        messages.error(request, 'No study selected')
        return redirect('select_study')
    
    patients = []
    
    with study_database_context(study):
        Patient = StudyModelLoader.get_model(study.code, 'Patient')
        if Patient:
            patients = Patient.objects.using(study.db_name).select_related('site').all()
    
    context = {
        'study': study,
        'patients': patients,
    }
    
    return render(request, 'studies/patient_list.html', context)


@login_required
def patient_detail(request, patient_id):
    """Patient detail view with visits and lab results"""
    study = getattr(request, 'study', None)
    
    if not study:
        messages.error(request, 'No study selected')
        return redirect('select_study')
    
    patient = None
    visits = []
    lab_results = []
    adverse_events = []
    
    with study_database_context(study):
        Patient = StudyModelLoader.get_model(study.code, 'Patient')
        if Patient:
            patient = get_object_or_404(
                Patient.objects.using(study.db_name),
                patient_id=patient_id
            )
            
            # Get related data
            visits = patient.visits.filter(is_deleted=False).order_by('-visit_date')
            lab_results = patient.lab_results.filter(is_deleted=False).order_by('-test_date')[:10]
            adverse_events = patient.adverse_events.filter(is_deleted=False).order_by('-start_date')
    
    context = {
        'study': study,
        'patient': patient,
        'visits': visits,
        'lab_results': lab_results,
        'adverse_events': adverse_events,
    }
    
    return render(request, 'studies/patient_detail.html', context)


@login_required
def data_export(request):
    """Export study data"""
    study = getattr(request, 'study', None)
    
    if not study:
        return JsonResponse({'error': 'No study selected'}, status=400)
    
    if request.method == 'POST':
        export_type = request.POST.get('export_type', 'csv')
        model_name = request.POST.get('model', 'Patient')
        
        # Get data
        data = []
        with study_database_context(study):
            Model = StudyModelLoader.get_model(study.code, model_name)
            if Model:
                queryset = Model.objects.using(study.db_name).all()
                
                # Convert to CSV or Excel
                import csv
                from django.http import HttpResponse
                
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{study.code}_{model_name}.csv"'
                
                if queryset.exists():
                    # Get field names
                    fields = [f.name for f in Model._meta.fields if not f.name.endswith('_ptr')]
                    
                    writer = csv.DictWriter(response, fieldnames=fields)
                    writer.writeheader()
                    
                    for obj in queryset:
                        row = {}
                        for field in fields:
                            value = getattr(obj, field)
                            row[field] = str(value) if value is not None else ''
                        writer.writerow(row)
                
                return response
    
    # Get available models for export
    models = StudyModelLoader.get_study_models(study.code)
    model_choices = [
        name for name, cls in models.items()
        if not (hasattr(cls._meta, 'abstract') and cls._meta.abstract)
    ]
    
    context = {
        'study': study,
        'model_choices': model_choices,
    }
    
    return render(request, 'studies/data_export.html', context)