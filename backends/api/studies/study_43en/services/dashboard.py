"""
Dashboard views and chart APIs for Study 43EN
Contains both main dashboard view and all chart data endpoints
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Count
from django.core.exceptions import FieldError
from collections import OrderedDict
from datetime import datetime, date
import logging

from .....studies.study_43en.models import (
    ScreeningCase, 
    EnrollmentCase, 
    ScreeningContact, 
    EnrollmentContact,
    SampleCollection,
    ContactSampleCollection
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

DB_ALIAS = 'db_study_43en'
TARGET_ENROLLMENT = 750


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_filtered_queryset(model, site_id):
    """
    Get filtered queryset using custom SiteFilteredManage
    
    Args:
        model: Django model class (must have site_objects manager)
        site_id: Site ID to filter by ('all' or specific site code)
        
    Returns:
        Filtered queryset using db_study_43en with site filter applied
    """
    return model.site_objects.using(DB_ALIAS).filter_by_site(site_id)


def add_percent_to_reasons(reason_qs):
    """
    Add percentage field to reasons queryset
    
    Args:
        reason_qs: QuerySet or list with 'count' field
        
    Returns:
        List of dicts with added 'percent' field
    """
    reasons = list(reason_qs)
    total = sum(r['count'] for r in reasons)
    
    for r in reasons:
        r['percent'] = round((r['count'] / total * 100), 1) if total > 0 else 0
    
    return reasons


# ============================================================================
# MAIN DASHBOARD VIEW
# ============================================================================

# backend/studies/study_43en/dashboard.py

@login_required
def home_dashboard(request):
    """Main dashboard view for Study 43EN"""
    
    # Get user's site access
    user_membership = getattr(request, 'user_membership', None)
    can_access_all = getattr(user_membership, 'can_access_all_sites', False) if user_membership else False
    user_site_codes = getattr(request, 'study_sites', [])
    user_site_codes = list(user_site_codes) if user_site_codes else []
    
    selected_site_id = request.session.get('selected_site_id')
    
    if selected_site_id and selected_site_id != 'all':
        site_filter = selected_site_id
    elif can_access_all:
        site_filter = 'all'
    else:
        site_filter = user_site_codes
    
    logger.debug(f"Loading dashboard for site filter: {site_filter}")
    
    try:
        study = getattr(request, 'study', None)
        study_code = '43en'
        study_folder = 'studies/study_43en'
        
        # ===== PATIENT STATISTICS =====
        if site_filter == 'all':
            screening_patients = ScreeningCase.objects.using(DB_ALIAS).count()
            enrolled_patients = (
                ScreeningCase.objects.using(DB_ALIAS)
                .filter(
                    UPPER16AGE=True,
                    INFPRIOR2OR48HRSADMIT=True,
                    ISOLATEDKPNFROMINFECTIONORBLOOD=True,
                    KPNISOUNTREATEDSTABLE=False,
                    CONSENTTOSTUDY=True
                )
                .count()
            )
        elif isinstance(site_filter, list):
            # Multiple sites - aggregate
            from django.db.models import Q
            q_objects = Q()
            for site_code in site_filter:
                q_objects |= Q(SITEID=site_code)
            
            screening_patients = ScreeningCase.objects.using(DB_ALIAS).filter(q_objects).count()
            enrolled_patients = (
                ScreeningCase.objects.using(DB_ALIAS)
                .filter(q_objects)
                .filter(
                    UPPER16AGE=True,
                    INFPRIOR2OR48HRSADMIT=True,
                    ISOLATEDKPNFROMINFECTIONORBLOOD=True,
                    KPNISOUNTREATEDSTABLE=False,
                    CONSENTTOSTUDY=True
                )
                .count()
            )
        else:
            # Single site - use manager
            screening_patients = get_filtered_queryset(ScreeningCase, site_filter).count()
            enrolled_patients = (
                get_filtered_queryset(ScreeningCase, site_filter)
                .filter(
                    UPPER16AGE=True,
                    INFPRIOR2OR48HRSADMIT=True,
                    ISOLATEDKPNFROMINFECTIONORBLOOD=True,
                    KPNISOUNTREATEDSTABLE=False,
                    CONSENTTOSTUDY=True
                )
                .count()
            )
        
        # ===== CONTACT STATISTICS - FIX QUAN TRỌNG =====
        if site_filter == 'all':
            screening_contacts = ScreeningContact.objects.using(DB_ALIAS).count()
            enrolled_contacts = EnrollmentContact.objects.using(DB_ALIAS).count()
            
        elif isinstance(site_filter, list):
            # Multiple sites - ScreeningContact có SITEID
            q_screening_contact = Q()
            for site_code in site_filter:
                q_screening_contact |= Q(SITEID=site_code)
            screening_contacts = ScreeningContact.objects.using(DB_ALIAS).filter(q_screening_contact).count()
            
            # EnrollmentContact KHÔNG có SITEID - phải qua USUBJID
            q_enrolled_contact = Q()
            for site_code in site_filter:
                q_enrolled_contact |= Q(USUBJID__SITEID=site_code)  # ← FIX: qua relationship
            enrolled_contacts = EnrollmentContact.objects.using(DB_ALIAS).filter(q_enrolled_contact).count()
            
        else:
            # Single site - use manager
            screening_contacts = get_filtered_queryset(ScreeningContact, site_filter).count()
            enrolled_contacts = get_filtered_queryset(EnrollmentContact, site_filter).count()
        
        # ===== PROJECT START DATE =====
        if site_filter == 'all':
            first_enrollment = (
                EnrollmentCase.objects.using(DB_ALIAS)
                .order_by('ENRDATE')
                .values_list('ENRDATE', flat=True)
                .first()
            )
        elif isinstance(site_filter, list):
            q_objects = Q()
            for site_code in site_filter:
                q_objects |= Q(USUBJID__SITEID=site_code)  # EnrollmentCase cũng qua USUBJID
            first_enrollment = (
                EnrollmentCase.objects.using(DB_ALIAS)
                .filter(q_objects)
                .order_by('ENRDATE')
                .values_list('ENRDATE', flat=True)
                .first()
            )
        else:
            first_enrollment = (
                get_filtered_queryset(EnrollmentCase, site_filter)
                .order_by('ENRDATE')
                .values_list('ENRDATE', flat=True)
                .first()
            )
        
        project_start = first_enrollment if first_enrollment else None
        percent_target = round(enrolled_patients / TARGET_ENROLLMENT * 100, 1) if enrolled_patients else 0
        
        # ===== UNRECRUITED REASONS =====
        if site_filter == 'all':
            patient_reasons_qs = (
                ScreeningCase.objects.using(DB_ALIAS)
                .filter(CONSENTTOSTUDY=False)
                .exclude(UNRECRUITED_REASON__isnull=True)
                .exclude(UNRECRUITED_REASON__exact='')
            )
            contact_reasons_qs = (
                ScreeningContact.objects.using(DB_ALIAS)
                .filter(CONSENTTOSTUDY=False)
            )
        elif isinstance(site_filter, list):
            q_objects = Q()
            for site_code in site_filter:
                q_objects |= Q(SITEID=site_code)
            
            patient_reasons_qs = (
                ScreeningCase.objects.using(DB_ALIAS)
                .filter(q_objects)
                .filter(CONSENTTOSTUDY=False)
                .exclude(UNRECRUITED_REASON__isnull=True)
                .exclude(UNRECRUITED_REASON__exact='')
            )
            contact_reasons_qs = (
                ScreeningContact.objects.using(DB_ALIAS)
                .filter(q_objects)
                .filter(CONSENTTOSTUDY=False)
            )
        else:
            patient_reasons_qs = (
                get_filtered_queryset(ScreeningCase, site_filter)
                .filter(CONSENTTOSTUDY=False)
                .exclude(UNRECRUITED_REASON__isnull=True)
                .exclude(UNRECRUITED_REASON__exact='')
            )
            contact_reasons_qs = (
                get_filtered_queryset(ScreeningContact, site_filter)
                .filter(CONSENTTOSTUDY=False)
            )
        
        patient_reasons = (
            patient_reasons_qs
            .values('UNRECRUITED_REASON')
            .annotate(count=Count('*'))
            .order_by('-count')
        )
        
        contact_not_consented = contact_reasons_qs.count()
        contact_reasons = [
            {'UNRECRUITED_REASON': 'Did not consent', 'count': contact_not_consented}
        ] if contact_not_consented > 0 else []
        
        context = {
            'study': study,
            'study_code': study_code,
            'study_name': study.safe_translation_getter('name') if study else '43EN Study',
            'study_folder': study_folder,
            'screening_patients': screening_patients,
            'enrolled_patients': enrolled_patients,
            'screening_contacts': screening_contacts,
            'enrolled_contacts': enrolled_contacts,
            'percent_target': percent_target,
            'target_enrollment': TARGET_ENROLLMENT,
            'project_start': project_start,
            'today': datetime.now(),
            'patient_reasons': add_percent_to_reasons(patient_reasons),
            'contact_reasons': add_percent_to_reasons(contact_reasons),
            'site_id': selected_site_id or 'all',
        }
        
        logger.debug(f"Dashboard loaded - Screening: {screening_patients}, Enrolled: {enrolled_patients}, Contacts: {enrolled_contacts}")
        return render(request, 'studies/study_43en/home_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in home_dashboard: {str(e)}", exc_info=True)
        return render(request, 'studies/study_43en/home_dashboard.html', {
            'error': str(e),
            'today': datetime.now(),
            'study_folder': 'studies/study_43en',
            'study_code': '43en',
        })

# ============================================================================
# CHART DATA APIs
# ============================================================================
def get_site_filter(request):
    """
    Determine site filter strategy based on user permissions and session
    
    Returns:
        tuple: (site_filter, filter_type) where:
            - site_filter: 'all', single site code, or list of site codes
            - filter_type: 'all', 'single', or 'multiple'
    """
    user_membership = getattr(request, 'user_membership', None)
    can_access_all = getattr(user_membership, 'can_access_all_sites', False) if user_membership else False
    user_site_codes = getattr(request, 'study_sites', [])
    user_site_codes = list(user_site_codes) if user_site_codes else []
    
    selected_site_id = request.session.get('selected_site_id')
    
    if selected_site_id and selected_site_id != 'all':
        return (selected_site_id, 'single')
    elif can_access_all:
        return ('all', 'all')
    else:
        return (user_site_codes, 'multiple')


# ============================================================================
# CHART DATA APIs - UPDATED
# ============================================================================

@require_GET
@login_required
def patient_cumulative_chart_data(request):
    """API: Patient cumulative enrollment by month"""
    site_filter, filter_type = get_site_filter(request)
    
    if filter_type == 'all':
        queryset = EnrollmentCase.objects.using(DB_ALIAS)
    elif filter_type == 'multiple':
        from django.db.models import Q
        q_objects = Q()
        for site_code in site_filter:
            q_objects |= Q(USUBJID__SITEID=site_code)
        queryset = EnrollmentCase.objects.using(DB_ALIAS).filter(q_objects)
    else:
        queryset = get_filtered_queryset(EnrollmentCase, site_filter)
    
    enroll_dates = queryset.values_list('ENRDATE', flat=True).order_by('ENRDATE')
    
    month_counts = OrderedDict()
    for d in enroll_dates:
        if d:
            month_str = d.strftime('%m/%Y')
            month_counts[month_str] = month_counts.get(month_str, 0) + 1
    
    cumulative = []
    total = 0
    for month in month_counts:
        total += month_counts[month]
        cumulative.append({'month': month, 'count': total})
    
    return JsonResponse({'data': cumulative})


@require_GET
@login_required
def contact_cumulative_chart_data(request):
    """API: Contact cumulative enrollment by date"""
    site_filter, filter_type = get_site_filter(request)
    
    if filter_type == 'all':
        queryset = EnrollmentContact.objects.using(DB_ALIAS)
    elif filter_type == 'multiple':
        from django.db.models import Q
        q_objects = Q()
        for site_code in site_filter:
            q_objects |= Q(USUBJID__SITEID=site_code)
        queryset = EnrollmentContact.objects.using(DB_ALIAS).filter(q_objects)
    else:
        queryset = get_filtered_queryset(EnrollmentContact, site_filter)
    
    enroll_dates = queryset.values_list('ENRDATE', flat=True).order_by('ENRDATE')
    
    date_counts = {}
    for d in enroll_dates:
        if d:
            date_str = d.strftime('%Y-%m-%d')
            date_counts[date_str] = date_counts.get(date_str, 0) + 1
    
    cumulative = []
    count = 0
    for date_key in sorted(date_counts.keys()):
        count += date_counts[date_key]
        cumulative.append({'date': date_key, 'count': count})
    
    return JsonResponse({'data': cumulative})


@require_GET
@login_required
def screening_comparison_chart_data(request):
    """API: Screening comparison between patients and contacts"""
    site_filter, filter_type = get_site_filter(request)
    
    if filter_type == 'all':
        patient_queryset = ScreeningCase.objects.using(DB_ALIAS)
        contact_queryset = ScreeningContact.objects.using(DB_ALIAS)
    elif filter_type == 'multiple':
        from django.db.models import Q
        q_objects = Q()
        for site_code in site_filter:
            q_objects |= Q(SITEID=site_code)
        patient_queryset = ScreeningCase.objects.using(DB_ALIAS).filter(q_objects)
        contact_queryset = ScreeningContact.objects.using(DB_ALIAS).filter(q_objects)
    else:
        patient_queryset = get_filtered_queryset(ScreeningCase, site_filter)
        contact_queryset = get_filtered_queryset(ScreeningContact, site_filter)
    
    patient_dates = patient_queryset.values_list('SCREENINGFORMDATE', flat=True)
    contact_dates = contact_queryset.values_list('SCREENINGFORMDATE', flat=True)
    
    patient_months = {}
    contact_months = {}
    
    for date in patient_dates:
        if date:
            month_key = date.strftime('%m/%Y')
            patient_months[month_key] = patient_months.get(month_key, 0) + 1
    
    for date in contact_dates:
        if date:
            month_key = date.strftime('%m/%Y')
            contact_months[month_key] = contact_months.get(month_key, 0) + 1
    
    all_dates = [d for d in list(patient_dates) + list(contact_dates) if d]
    if not all_dates:
        return JsonResponse({'data': {
            'labels': [], 'patients': [], 'contacts': [],
            'patientsCumulative': [], 'contactsCumulative': []
        }})
    
    min_date = min(all_dates)
    max_date = max(all_dates)
    
    current_date = datetime(min_date.year, min_date.month, 1)
    end_date = datetime(max_date.year, max_date.month, 1)
    
    months = []
    while current_date <= end_date:
        months.append(current_date.strftime('%m/%Y'))
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)
    
    patients_data = []
    contacts_data = []
    patients_cumulative = []
    contacts_cumulative = []
    
    patient_cum = 0
    contact_cum = 0
    
    for month in months:
        patient_count = patient_months.get(month, 0)
        contact_count = contact_months.get(month, 0)
        
        patients_data.append(patient_count)
        contacts_data.append(contact_count)
        
        patient_cum += patient_count
        contact_cum += contact_count
        
        patients_cumulative.append(patient_cum)
        contacts_cumulative.append(contact_cum)
    
    return JsonResponse({
        'data': {
            'labels': months,
            'patients': patients_data,
            'contacts': contacts_data,
            'patientsCumulative': patients_cumulative,
            'contactsCumulative': contacts_cumulative
        }
    })


@require_GET
@login_required
def gender_distribution_chart_data(request):
    """API: Gender distribution for enrolled patients and contacts"""
    try:
        site_filter, filter_type = get_site_filter(request)
        
        # Patient gender
        if filter_type == 'all':
            patient_queryset = EnrollmentCase.objects.using(DB_ALIAS)
        elif filter_type == 'multiple':
            from django.db.models import Q
            q_objects = Q()
            for site_code in site_filter:
                q_objects |= Q(USUBJID__SITEID=site_code)
            patient_queryset = EnrollmentCase.objects.using(DB_ALIAS).filter(q_objects)
        else:
            patient_queryset = get_filtered_queryset(EnrollmentCase, site_filter)
        
        patient_gender_counts = patient_queryset.values('SEX').annotate(count=Count('SEX'))
        patient_data = {'male': 0, 'female': 0}
        for item in patient_gender_counts:
            if item['SEX'] == 'Male':
                patient_data['male'] = item['count']
            elif item['SEX'] == 'Female':
                patient_data['female'] = item['count']
        
        # Contact gender
        if filter_type == 'all':
            contact_queryset = EnrollmentContact.objects.using(DB_ALIAS)
        elif filter_type == 'multiple':
            q_objects = Q()
            for site_code in site_filter:
                q_objects |= Q(USUBJID__SITEID=site_code)
            contact_queryset = EnrollmentContact.objects.using(DB_ALIAS).filter(q_objects)
        else:
            contact_queryset = get_filtered_queryset(EnrollmentContact, site_filter)
        
        contact_gender_counts = contact_queryset.values('SEX').annotate(count=Count('SEX'))
        contact_data = {'male': 0, 'female': 0}
        for item in contact_gender_counts:
            if item['SEX'] == 'Male':
                contact_data['male'] = item['count']
            elif item['SEX'] == 'Female':
                contact_data['female'] = item['count']
        
        return JsonResponse({
            'data': {
                'patient': {
                    'labels': ['Nam', 'Nữ'],
                    'data': [patient_data['male'], patient_data['female']],
                    'colors': ['#36A2EB', '#FF6384']
                },
                'contact': {
                    'labels': ['Nam', 'Nữ'],
                    'data': [contact_data['male'], contact_data['female']],
                    'colors': ['#36A2EB', '#FF6384']
                }
            }
        })
    except Exception as e:
        logger.error(f"Error in gender_distribution_chart_data: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@login_required
def patient_enrollment_chart_data(request):
    """API: Patient enrollment by month with cumulative"""
    site_filter, filter_type = get_site_filter(request)
    
    if filter_type == 'all':
        queryset = EnrollmentCase.objects.using(DB_ALIAS)
    elif filter_type == 'multiple':
        from django.db.models import Q
        q_objects = Q()
        for site_code in site_filter:
            q_objects |= Q(USUBJID__SITEID=site_code)
        queryset = EnrollmentCase.objects.using(DB_ALIAS).filter(q_objects)
    else:
        queryset = get_filtered_queryset(EnrollmentCase, site_filter)
    
    enroll_dates = queryset.values_list('ENRDATE', flat=True).order_by('ENRDATE')
    
    monthly_counts = {}
    for date_val in enroll_dates:
        if date_val:
            month_key = date_val.strftime('%m/%Y')
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
    
    dates_filtered = [d for d in enroll_dates if d]
    if not dates_filtered:
        return JsonResponse({
            'data': {
                'labels': [],
                'monthly': [],
                'cumulative': [],
                'target': TARGET_ENROLLMENT
            }
        })
    
    min_date = min(dates_filtered)
    max_date = max(dates_filtered)
    
    current_date = datetime(min_date.year, min_date.month, 1)
    end_date = datetime(max_date.year, max_date.month, 1)
    
    months = []
    while current_date <= end_date:
        months.append(current_date.strftime('%m/%Y'))
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)
    
    monthly_data = []
    cumulative_data = []
    cumulative = 0
    
    for month in months:
        month_count = monthly_counts.get(month, 0)
        monthly_data.append(month_count)
        cumulative += month_count
        cumulative_data.append(cumulative)
    
    return JsonResponse({
        'data': {
            'labels': months,
            'monthly': monthly_data,
            'cumulative': cumulative_data,
            'target': TARGET_ENROLLMENT
        }
    })


@require_GET
@login_required
def sample_distribution_chart_data(request):
    """API: Sample distribution for patients and contacts"""
    try:
        site_filter, filter_type = get_site_filter(request)
        
        sample_types = {
            'Phân': 'STOOL',
            'Phết trực tràng': 'RECTSWAB',
            'Phết họng': 'THROATSWAB',
            'Máu': 'BLOOD'
        }
        
        colors = {
            'Phân': '#FF6384',
            'Phết trực tràng': '#36A2EB',
            'Phết họng': '#FFCE56',
            'Máu': '#4BC0C0'
        }
        
        # ===== PATIENT SAMPLES =====
        patient_counts = {}
        
        for name, field in sample_types.items():
            if filter_type == 'all':
                queryset = SampleCollection.objects.using(DB_ALIAS)
            elif filter_type == 'multiple':
                from django.db.models import Q
                q_objects = Q()
                for site_code in site_filter:
                    q_objects |= Q(USUBJID__USUBJID__SITEID=site_code)
                queryset = SampleCollection.objects.using(DB_ALIAS).filter(q_objects)
            else:
                queryset = get_filtered_queryset(SampleCollection, site_filter)
            
            count = queryset.filter(**{field: True}).count()
            if count > 0:
                patient_counts[name] = patient_counts.get(name, 0) + count
        
        for suffix in ['_2', '_3', '_4']:
            for name, field in sample_types.items():
                if name == 'Máu' and suffix == '_4':
                    continue
                    
                field_name = f"{field}{suffix}"
                try:
                    if filter_type == 'all':
                        queryset = SampleCollection.objects.using(DB_ALIAS)
                    elif filter_type == 'multiple':
                        q_objects = Q()
                        for site_code in site_filter:
                            q_objects |= Q(USUBJID__USUBJID__SITEID=site_code)
                        queryset = SampleCollection.objects.using(DB_ALIAS).filter(q_objects)
                    else:
                        queryset = get_filtered_queryset(SampleCollection, site_filter)
                    
                    count = queryset.filter(**{field_name: True}).count()
                    if count > 0:
                        patient_counts[name] = patient_counts.get(name, 0) + count
                except FieldError:
                    continue
        
        # ===== CONTACT SAMPLES =====
        contact_counts = {}
        
        for name, field in sample_types.items():
            if filter_type == 'all':
                queryset = ContactSampleCollection.objects.using(DB_ALIAS)
            elif filter_type == 'multiple':
                q_objects = Q()
                for site_code in site_filter:
                    q_objects |= Q(USUBJID__USUBJID__SITEID=site_code)
                queryset = ContactSampleCollection.objects.using(DB_ALIAS).filter(q_objects)
            else:
                queryset = get_filtered_queryset(ContactSampleCollection, site_filter)
            
            count = queryset.filter(**{field: True}).count()
            if count > 0:
                contact_counts[name] = contact_counts.get(name, 0) + count
        
        for suffix in ['_3', '_4']:
            for name, field in sample_types.items():
                if name == 'Máu':
                    continue
                    
                field_name = f"{field}{suffix}"
                try:
                    if filter_type == 'all':
                        queryset = ContactSampleCollection.objects.using(DB_ALIAS)
                    elif filter_type == 'multiple':
                        q_objects = Q()
                        for site_code in site_filter:
                            q_objects |= Q(USUBJID__USUBJID__SITEID=site_code)
                        queryset = ContactSampleCollection.objects.using(DB_ALIAS).filter(q_objects)
                    else:
                        queryset = get_filtered_queryset(ContactSampleCollection, site_filter)
                    
                    count = queryset.filter(**{field_name: True}).count()
                    if count > 0:
                        contact_counts[name] = contact_counts.get(name, 0) + count
                except FieldError:
                    continue
        
        return JsonResponse({
            'data': {
                'patient': {
                    'labels': list(patient_counts.keys()),
                    'counts': list(patient_counts.values()),
                    'colors': [colors.get(name, '#9966FF') for name in patient_counts.keys()]
                },
                'contact': {
                    'labels': list(contact_counts.keys()),
                    'counts': list(contact_counts.values()),
                    'colors': [colors.get(name, '#9966FF') for name in contact_counts.keys()]
                }
            }
        })
    except Exception as e:
        logger.error(f"Error in sample_distribution_chart_data: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)