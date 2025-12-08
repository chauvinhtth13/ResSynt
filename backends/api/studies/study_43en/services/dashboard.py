"""
Dashboard views and chart APIs for Study 43EN
 REFACTORED: Sử dụng site_utils thống nhất với views khác
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Count, Avg, F, ExpressionWrapper, IntegerField, Q, Case, When
from django.core.exceptions import FieldError
from collections import OrderedDict
from datetime import datetime, date
import logging

from django.db.models.functions import Extract

#  IMPORT TỪ SITE_UTILS (thay vì define riêng)
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset
)

from backends.studies.study_43en.models import (
    SCR_CASE, 
    ENR_CASE, 
    SCR_CONTACT, 
    ENR_CONTACT,
    SAM_CASE,
    SAM_CONTACT,
    CLI_CASE,
    AntibioticSensitivity
)
from backends.studies.study_43en.models.patient import DISCH_CASE, FU_CASE_28, FU_CASE_90

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

DB_ALIAS = 'db_study_43en'
TARGET_ENROLLMENT = 750


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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

def get_enrolled_patients_queryset(site_filter, filter_type):
    """
     CENTRALIZED: Get enrolled patients queryset
    Use this everywhere to ensure consistency
    """
    return get_filtered_queryset(SCR_CASE, site_filter, filter_type).filter(
        UPPER16AGE=True,
        INFPRIOR2OR48HRSADMIT=True,
        ISOLATEDKPNFROMINFECTIONORBLOOD=True,
        KPNISOUNTREATEDSTABLE=False,
        CONSENTTOSTUDY=True
    )


@login_required
def home_dashboard(request):
    """
    Main dashboard view for Study 43EN
    """
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.debug(f"Loading dashboard - Site: {site_filter}, Type: {filter_type}")
    
    try:
        study = getattr(request, 'study', None)
        study_code = '43en'
        study_folder = 'studies/study_43en'
        
        # ===== STUDY INFO =====
        study_name = "Klebsiella pneumoniae Epidemiology Study"
        site_name = "All Sites"
        
        # Lấy site name nếu có filter
        if site_filter and site_filter != 'all':
            from backends.tenancy.models import Site
            try:
                if filter_type == 'single':
                    site = Site.objects.get(code=site_filter)
                    site_name = site.name
                elif filter_type == 'multiple':
                    sites = Site.objects.filter(code__in=site_filter)
                    site_count = sites.count()
                    site_names = ', '.join([s.code for s in sites[:3]])
                    site_name = f"{site_names}" + (f" (+{site_count - 3} more)" if site_count > 3 else "")
            except Site.DoesNotExist:
                site_name = f"Site {site_filter}"
        
        # ===== PATIENT STATISTICS =====
        screening_patients = get_filtered_queryset(SCR_CASE, site_filter, filter_type).count()
        
        #  Use centralized function
        enrolled_patients = get_enrolled_patients_queryset(site_filter, filter_type).count()
        
        logger.info(f"[Dashboard] Screening: {screening_patients}, Enrolled: {enrolled_patients}")
        
        # ===== CONTACT STATISTICS =====
        screening_contacts = get_filtered_queryset(SCR_CONTACT, site_filter, filter_type).count()
        enrolled_contacts = get_filtered_queryset(ENR_CONTACT, site_filter, filter_type).count()
        
        # ===== PROJECT START DATE =====
        first_enrollment = (
            get_filtered_queryset(ENR_CASE, site_filter, filter_type)
            .order_by('ENRDATE')
            .values_list('ENRDATE', flat=True)
            .first()
        )
        
        project_start = first_enrollment if first_enrollment else None
        raw_percent = (enrolled_patients / TARGET_ENROLLMENT * 100) if enrolled_patients else 0.0
        percent_target = f"{raw_percent:.1f}"  # Format as string with 1 decimal
        

        avg_hospital_stay = get_average_hospital_stay(site_filter, filter_type)
        mortality_stats = get_mortality_rate(site_filter, filter_type)
        
        logger.info(f"[Dashboard] Mortality stats:")
        logger.info(f"  - Dashboard enrolled: {enrolled_patients}")
        logger.info(f"  - Mortality enrolled: {mortality_stats['total_enrolled']}")
        logger.info(f"  - Match: {enrolled_patients == mortality_stats['total_enrolled']}")

        # ===== UNRECRUITED REASONS =====
        patient_reasons = (
            get_filtered_queryset(SCR_CASE, site_filter, filter_type)
            .filter(CONSENTTOSTUDY=False)
            .exclude(UNRECRUITED_REASON__isnull=True)
            .exclude(UNRECRUITED_REASON__exact='')
            .values('UNRECRUITED_REASON')
            .annotate(count=Count('*'))
            .order_by('-count')
        )
        
        contact_not_consented = (
            get_filtered_queryset(SCR_CONTACT, site_filter, filter_type)
            .filter(CONSENTTOSTUDY=False)
            .count()
        )
        
        contact_reasons = [
            {'UNRECRUITED_REASON': 'Did not consent', 'count': contact_not_consented}
        ] if contact_not_consented > 0 else []
        
        context = {
            'study': study,
            'study_code': study_code,
            'study_folder': study_folder,
            'study_name': study_name,
            'site_name': site_name,
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
            'site_id': site_filter,
            'filter_type': filter_type,
            'avg_hospital_stay': avg_hospital_stay,
            'mortality_rate': f"{mortality_stats['mortality_rate']:.1f}",  # Format as string with 1 decimal
            'total_deaths': mortality_stats['total_deaths'],
            'total_enrolled_for_mortality': mortality_stats['total_enrolled'], 
        }
        
        logger.debug(f"Dashboard loaded successfully")
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
# CHART DATA APIs -  REFACTORED
# ============================================================================

@require_GET
@login_required
def patient_cumulative_chart_data(request):
    """API: Patient cumulative enrollment by month"""
    site_filter, filter_type = get_site_filter_params(request)
    
    queryset = get_filtered_queryset(ENR_CASE, site_filter, filter_type)
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
    site_filter, filter_type = get_site_filter_params(request)
    
    queryset = get_filtered_queryset(ENR_CONTACT, site_filter, filter_type)
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
    site_filter, filter_type = get_site_filter_params(request)
    
    patient_queryset = get_filtered_queryset(SCR_CASE, site_filter, filter_type)
    contact_queryset = get_filtered_queryset(SCR_CONTACT, site_filter, filter_type)
    
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
        site_filter, filter_type = get_site_filter_params(request)
        
        # Patient gender
        patient_queryset = get_filtered_queryset(ENR_CASE, site_filter, filter_type)
        patient_gender_counts = patient_queryset.values('SEX').annotate(count=Count('SEX'))
        
        patient_data = {'male': 0, 'female': 0}
        for item in patient_gender_counts:
            if item['SEX'] == 'Male':
                patient_data['male'] = item['count']
            elif item['SEX'] == 'Female':
                patient_data['female'] = item['count']
        
        # Contact gender
        contact_queryset = get_filtered_queryset(ENR_CONTACT, site_filter, filter_type)
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
    site_filter, filter_type = get_site_filter_params(request)
    
    queryset = get_filtered_queryset(ENR_CASE, site_filter, filter_type)
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
        site_filter, filter_type = get_site_filter_params(request)
        
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
            queryset = get_filtered_queryset(SAM_CASE, site_filter, filter_type)
            count = queryset.filter(**{field: True}).count()
            if count > 0:
                patient_counts[name] = patient_counts.get(name, 0) + count
        
        for suffix in ['_2', '_3', '_4']:
            for name, field in sample_types.items():
                if name == 'Máu' and suffix == '_4':
                    continue
                
                field_name = f"{field}{suffix}"
                try:
                    queryset = get_filtered_queryset(SAM_CASE, site_filter, filter_type)
                    count = queryset.filter(**{field_name: True}).count()
                    if count > 0:
                        patient_counts[name] = patient_counts.get(name, 0) + count
                except FieldError:
                    continue
        
        # ===== CONTACT SAMPLES =====
        contact_counts = {}
        
        for name, field in sample_types.items():
            queryset = get_filtered_queryset(SAM_CONTACT, site_filter, filter_type)
            count = queryset.filter(**{field: True}).count()
            if count > 0:
                contact_counts[name] = contact_counts.get(name, 0) + count
        
        for suffix in ['_3', '_4']:
            for name, field in sample_types.items():
                if name == 'Máu':
                    continue
                
                field_name = f"{field}{suffix}"
                try:
                    queryset = get_filtered_queryset(SAM_CONTACT, site_filter, filter_type)
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


@require_GET
@login_required
def infection_focus_chart_data(request):
    """API: Infection focus distribution"""
    site_filter, filter_type = get_site_filter_params(request)
    
    queryset = get_filtered_queryset(CLI_CASE, site_filter, filter_type)
    
    focus_counts = (
        queryset
        .exclude(INFECTFOCUS48H__isnull=True)
        .exclude(INFECTFOCUS48H__exact='')
        .values('INFECTFOCUS48H')
        .annotate(count=Count('*'))
        .order_by('-count')
    )
    
    labels = []
    counts = []
    colors = {
        'Pneumonia': '#FF6384',        # Đỏ hồng
        'UTI': '#36A2EB',              # Xanh dương
        'AbdAbscess': '#FFCE56',       # Vàng
        'Peritonitis': '#4BC0C0',      # Xanh ngọc
        'SoftTissue': '#9966FF',       # Tím
        'Meningitis': '#FF9F40',       # Cam
        'NTTKTW': '#8B4513',           #  CHANGED: Nâu (khác với Empyema)
        'Empyema': '#696969',          #  CHANGED: Xám đậm
        'Other': '#C9CBCF'             # Xám nhạt
    }
    
    chart_colors = []
    for item in focus_counts:
        focus = item['INFECTFOCUS48H']
        labels.append(dict(CLI_CASE.InfectFocus48HChoices.choices).get(focus, focus))
        counts.append(item['count'])
        chart_colors.append(colors.get(focus, '#808080'))
    
    return JsonResponse({
        'data': {
            'labels': labels,
            'counts': counts,
            'colors': chart_colors
        }
    })


@require_GET
@login_required
def antibiotic_resistance_chart_data(request):
    """API: Antibiotic resistance overview"""
    site_filter, filter_type = get_site_filter_params(request)
    
    #  SIMPLIFIED: Sử dụng get_filtered_queryset thống nhất
    queryset = get_filtered_queryset(AntibioticSensitivity, site_filter, filter_type)
    queryset = queryset.exclude(SENSITIVITY_LEVEL='ND')
    
    antibiotic_stats = {}
    
    for record in queryset.values('ANTIBIOTIC_NAME', 'SENSITIVITY_LEVEL'):
        abx = record['ANTIBIOTIC_NAME']
        sens = record['SENSITIVITY_LEVEL']
        
        if abx not in antibiotic_stats:
            antibiotic_stats[abx] = {'total': 0, 'resistant': 0, 'sensitive': 0}
        
        antibiotic_stats[abx]['total'] += 1
        if sens == 'R':
            antibiotic_stats[abx]['resistant'] += 1
        elif sens == 'S':
            antibiotic_stats[abx]['sensitive'] += 1
    
    resistance_data = []
    for abx, stats in antibiotic_stats.items():
        if stats['total'] >= 5:
            resistance_pct = round((stats['resistant'] / stats['total']) * 100, 1)
            resistance_data.append({
                'antibiotic': abx,
                'resistance_pct': resistance_pct,
                'total': stats['total']
            })
    
    resistance_data.sort(key=lambda x: x['resistance_pct'], reverse=True)
    top_10 = resistance_data[:10]
    
    return JsonResponse({
        'data': {
            'labels': [item['antibiotic'] for item in top_10],
            'resistance': [item['resistance_pct'] for item in top_10],
            'totals': [item['total'] for item in top_10]
        }
    })


@require_GET
@login_required
def resistance_by_comorbidity_data(request):
    """API: Antibiotic resistance rates by underlying conditions"""
    site_filter, filter_type = get_site_filter_params(request)
    
    try:
        enrollment_qs = get_filtered_queryset(ENR_CASE, site_filter, filter_type)
        
        conditions_to_check = {
            'Diabetes': 'DIABETES',
            'CKD': 'KIDNEYDISEASE',
            'Cancer': 'CANCER',
            'HIV/AIDS': 'HIV',
            'Cirrhosis': 'CIRRHOSIS',
            'COPD': 'COPD',
            'Heart Failure': 'HEARTFAILURE'
        }
        
        results = {}
        
        for condition_name, condition_field in conditions_to_check.items():
            patients_with_condition = []
            
            for enrollment in enrollment_qs.select_related('Underlying_Condition'):
                try:
                    underlying = enrollment.Underlying_Condition
                    if underlying and getattr(underlying, condition_field, False):
                        usubjid_str = enrollment.USUBJID.USUBJID
                        patients_with_condition.append(usubjid_str)
                except Exception as e:
                    logger.debug(f"Error checking condition for {enrollment.USUBJID}: {e}")
                    continue
            
            if not patients_with_condition:
                continue
            
            #  SIMPLIFIED: Sử dụng get_filtered_queryset
            ast_qs = get_filtered_queryset(AntibioticSensitivity, site_filter, filter_type)
            ast_qs = ast_qs.filter(
                LAB_CULTURE_ID__USUBJID__USUBJID__USUBJID__in=patients_with_condition
            ).exclude(SENSITIVITY_LEVEL='ND')
            
            total = ast_qs.count()
            
            if total < 5:
                continue
            
            resistant = ast_qs.filter(SENSITIVITY_LEVEL='R').count()
            sensitive = ast_qs.filter(SENSITIVITY_LEVEL='S').count()
            intermediate = ast_qs.filter(SENSITIVITY_LEVEL='I').count()
            
            resistance_rate = round((resistant / total) * 100, 1)
            
            results[condition_name] = {
                'resistance_rate': resistance_rate,
                'total_tests': total,
                'resistant_tests': resistant,
                'sensitive_tests': sensitive,
                'intermediate_tests': intermediate,
                'patient_count': len(patients_with_condition)
            }
        
        sorted_results = dict(sorted(results.items(), key=lambda x: x[1]['resistance_rate'], reverse=True))
        
        return JsonResponse({
            'data': sorted_results,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in resistance_by_comorbidity_data: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)


# ============================================================================
# HELPER FUNCTIONS FOR METRICS -  UPDATED
# ============================================================================

def get_average_hospital_stay(site_filter, filter_type):
    """
     UPDATED: Nhận thêm filter_type parameter
    Tính thời gian nằm viện trung bình
    """
    discharges = get_filtered_queryset(DISCH_CASE, site_filter, filter_type)
    
    discharges_with_stay = discharges.select_related(
        'USUBJID__clinical_case'
    ).filter(
        DISCHDATE__isnull=False,
        USUBJID__clinical_case__ADMISDATE__isnull=False
    ).annotate(
        stay_days=ExpressionWrapper(
            Extract(F('DISCHDATE') - F('USUBJID__clinical_case__ADMISDATE'), 'day') + 1,
            output_field=IntegerField()
        )
    )
    
    avg_stay = discharges_with_stay.aggregate(
        avg_days=Avg('stay_days')
    )['avg_days']
    
    return round(avg_stay, 1) if avg_stay else None


def get_mortality_rate(site_filter, filter_type):
    """
    Calculate mortality rate from all enrolled patients
     FIXED: Use enrolled patients from SCR_CASE (same as dashboard)
    """
    #  Use centralized function
    enrolled_qs = get_enrolled_patients_queryset(site_filter, filter_type)
    total_enrolled = enrolled_qs.count()
    
    logger.info(f"[Mortality] Total enrolled from SCR_CASE: {total_enrolled}")
    
    if total_enrolled == 0:
        return {
            'total_enrolled': 0,
            'total_deaths': 0,
            'mortality_rate': 0.0
        }
    
    enrolled_usubjids = list(enrolled_qs.values_list('USUBJID', flat=True))
    logger.info(f"[Mortality] Enrolled USUBJID count: {len(enrolled_usubjids)}")
    
    deaths_at_discharge = get_filtered_queryset(DISCH_CASE, site_filter, filter_type).filter(
        USUBJID__in=enrolled_usubjids,  
        DEATHATDISCH='Yes'
    ).values_list('USUBJID', flat=True)
    
    deaths_at_fu28 = get_filtered_queryset(FU_CASE_28, site_filter, filter_type).filter(
        USUBJID__in=enrolled_usubjids,  
        Dead='Yes'
    ).values_list('USUBJID', flat=True)
    
    deaths_at_fu90 = get_filtered_queryset(FU_CASE_90, site_filter, filter_type).filter(
        USUBJID__in=enrolled_usubjids,  
        Dead='Yes'
    ).values_list('USUBJID', flat=True)
    
    all_death_usubjids = set(deaths_at_discharge) | set(deaths_at_fu28) | set(deaths_at_fu90)
    total_deaths = len(all_death_usubjids)
    
    # Calculate with explicit decimal precision
    raw_rate = (total_deaths / total_enrolled) * 100
    mortality_rate = round(raw_rate, 1)
    
    logger.info(f"[Mortality] Deaths breakdown:")
    logger.info(f"  - At discharge: {len(deaths_at_discharge)}")
    logger.info(f"  - At FU-28: {len(deaths_at_fu28)}")
    logger.info(f"  - At FU-90: {len(deaths_at_fu90)}")
    logger.info(f"  - Total unique deaths: {total_deaths}")
    logger.info(f"  - Raw rate: {raw_rate}")
    logger.info(f"  - Rounded rate: {mortality_rate}")
    logger.info(f"  - Mortality rate: {total_deaths}/{total_enrolled} = {mortality_rate}%")
    
    return {
        'total_enrolled': total_enrolled,
        'total_deaths': total_deaths,
        'mortality_rate': mortality_rate
    }