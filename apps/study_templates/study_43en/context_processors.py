# Trong file context_processors.py
from datetime import date, timedelta
from study_43en.models import ExpectedDates

def upcoming_appointments(request):
    """Cung cấp thông tin về các lịch hẹn sắp tới trong 3 ngày tới"""
    if not request.user.is_authenticated:
        return {'upcoming_count': 0, 'upcoming_patients': []}
    
    today = date.today()
    upcoming_date = today + timedelta(days=3)
    
    # Tìm tất cả ngày dự kiến trong 3 ngày tới
    upcoming = []
    
    # Kiểm tra d10
    d10_appointments = ExpectedDates.objects.filter(
        d10_expected_date__gte=today,
        d10_expected_date__lte=upcoming_date
    ).select_related('enrollment_case__USUBJID')
    
    for appt in d10_appointments:
        upcoming.append({
            'patient_name': appt.enrollment_case.USUBJID.INITIAL,
            'expected_date': appt.d10_expected_date,
            'visit_type': 'V2 (D10)',
            'usubjid': appt.enrollment_case.USUBJID.USUBJID,
        })
    
    # Kiểm tra d28
    d28_appointments = ExpectedDates.objects.filter(
        d28_expected_date__gte=today,
        d28_expected_date__lte=upcoming_date
    ).select_related('enrollment_case__USUBJID')
    
    for appt in d28_appointments:
        upcoming.append({
            'patient_name': appt.enrollment_case.USUBJID.INITIAL,
            'expected_date': appt.d28_expected_date,
            'visit_type': 'V3 (D28)',
            'usubjid': appt.enrollment_case.USUBJID.USUBJID,
        })
    
    # Kiểm tra d90
    d90_appointments = ExpectedDates.objects.filter(
        d90_expected_date__gte=today,
        d90_expected_date__lte=upcoming_date
    ).select_related('enrollment_case__USUBJID')
    
    for appt in d90_appointments:
        upcoming.append({
            'patient_name': appt.enrollment_case.USUBJID.INITIAL,
            'expected_date': appt.d90_expected_date,
            'visit_type': 'V4 (D90)',
            'usubjid': appt.enrollment_case.USUBJID.USUBJID,
        })
    
    # Sắp xếp theo ngày
    upcoming.sort(key=lambda x: x['expected_date'])
    
    return {
        'upcoming_count': len(upcoming),
        'upcoming_patients': upcoming
    }