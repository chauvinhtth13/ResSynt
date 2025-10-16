# Trong file context_processors.py
from datetime import date, timedelta
from backends.studies.study_43en.models.schedule import (
    FollowUpStatus, ExpectedDates
)
# def site_filter_context(request):
#     """Cung cấp thông tin về site được chọn cho các template"""
#     # Lấy danh sách các site có sẵn
#     available_sites = [
#         # Không thêm 'all' option ở đây để tránh duplicate với template
#         {'id': '003', 'name': 'Site 003'},
#         {'id': '011', 'name': 'Site 011'},
#         {'id': '020', 'name': 'Site 020'},
#     ]
    
#     # Lấy site được chọn từ session hoặc request, mặc định là 'all'
#     selected_site_id = request.session.get('selected_site_id', 'all')
    
#     # Debug để theo dõi
#     print(f"CONTEXT_PROCESSOR: selected_site_id = {selected_site_id}")
    
#     return {
#         'available_sites': available_sites,
#         'selected_site_id': selected_site_id
#     }

def upcoming_appointments(request):
    """Cung cấp thông tin về các lịch hẹn sắp tới trong 3 ngày tới - có lọc theo site"""
    if not request.user.is_authenticated:
        return {'upcoming_count': 0, 'upcoming_patients': []}
    
    today = date.today()
    upcoming_date = today + timedelta(days=3)
    
    # Lấy site_id từ request (đã được xử lý bởi middleware), fallback đến session
    site_id = getattr(request, 'selected_site_id', None) or request.session.get('selected_site_id', 'all')
    print(f"CONTEXT_PROCESSOR upcoming_appointments: selected_site_id = {site_id}")
    print(f"CONTEXT_PROCESSOR: Filtering notifications for site = {site_id}")
    
    # Tìm tất cả ngày dự kiến trong 3 ngày tới - với site filtering
    upcoming = []
    
    # === KIỂM TRA V2 APPOINTMENTS (D10) ===
    print(f"NOTIFICATION: Checking V2 appointments for site {site_id}")
    if site_id and site_id != 'all':
        # Lọc theo site cụ thể
        v2_appointments = ExpectedDates.site_objects.filter_by_site(site_id).filter(
            V2_EXPECTED_DATE__gte=today,
            V2_EXPECTED_DATE__lte=upcoming_date,
            V2_EXPECTED_DATE__isnull=False  # Chỉ lấy những appointment có ngày
        ).select_related('USUBJID__USUBJID')
        print(f"NOTIFICATION: Found {v2_appointments.count()} V2 appointments for site {site_id}")
    else:
        # Lấy tất cả sites khi chọn 'all'
        v2_appointments = ExpectedDates.objects.filter(
            V2_EXPECTED_DATE__gte=today,
            V2_EXPECTED_DATE__lte=upcoming_date,
            V2_EXPECTED_DATE__isnull=False
        ).select_related('USUBJID__USUBJID')
        print(f"NOTIFICATION: Found {v2_appointments.count()} V2 appointments for ALL sites")
    
    for appt in v2_appointments:
        try:
            # Lấy thông tin bệnh nhân với error handling
            patient_name = 'N/A'
            usubjid = 'N/A'
            site_code = 'N/A'
            
            if hasattr(appt.USUBJID, 'USUBJID') and appt.USUBJID.USUBJID:
                if hasattr(appt.USUBJID.USUBJID, 'INITIAL'):
                    patient_name = appt.USUBJID.USUBJID.INITIAL or 'N/A'
                if hasattr(appt.USUBJID.USUBJID, 'USUBJID'):
                    usubjid = appt.USUBJID.USUBJID.USUBJID or 'N/A'
                    # Trích xuất site code từ USUBJID (format: 003-A-001)
                    if usubjid and '-' in usubjid:
                        site_code = usubjid.split('-')[0]
                        
            upcoming.append({
                'patient_name': patient_name,
                'expected_date': appt.V2_EXPECTED_DATE,
                'visit_type': 'V2 (D10)',
                'usubjid': usubjid,
                'site_code': site_code,  # Thêm site_code để debug
                'notification_type': 'V2_VISIT'
            })
            print(f"NOTIFICATION V2: {usubjid} ({site_code}) - {patient_name} - {appt.V2_EXPECTED_DATE}")
        except Exception as e:
            print(f"Error processing V2 appointment: {e}")
            continue
    
    # === KIỂM TRA V3 APPOINTMENTS (D28) ===
    print(f"NOTIFICATION: Checking V3 appointments for site {site_id}")
    if site_id and site_id != 'all':
        v3_appointments = ExpectedDates.site_objects.filter_by_site(site_id).filter(
            V3_EXPECTED_DATE__gte=today,
            V3_EXPECTED_DATE__lte=upcoming_date,
            V3_EXPECTED_DATE__isnull=False
        ).select_related('USUBJID__USUBJID')
        print(f"NOTIFICATION: Found {v3_appointments.count()} V3 appointments for site {site_id}")
    else:
        v3_appointments = ExpectedDates.objects.filter(
            V3_EXPECTED_DATE__gte=today,
            V3_EXPECTED_DATE__lte=upcoming_date,
            V3_EXPECTED_DATE__isnull=False
        ).select_related('USUBJID__USUBJID')
        print(f"NOTIFICATION: Found {v3_appointments.count()} V3 appointments for ALL sites")
    
    for appt in v3_appointments:
        try:
            patient_name = 'N/A'
            usubjid = 'N/A'
            site_code = 'N/A'
            
            if hasattr(appt.USUBJID, 'USUBJID') and appt.USUBJID.USUBJID:
                if hasattr(appt.USUBJID.USUBJID, 'INITIAL'):
                    patient_name = appt.USUBJID.USUBJID.INITIAL or 'N/A'
                if hasattr(appt.USUBJID.USUBJID, 'USUBJID'):
                    usubjid = appt.USUBJID.USUBJID.USUBJID or 'N/A'
                    if usubjid and '-' in usubjid:
                        site_code = usubjid.split('-')[0]
                        
            upcoming.append({
                'patient_name': patient_name,
                'expected_date': appt.V3_EXPECTED_DATE,
                'visit_type': 'V3 (D28)',
                'usubjid': usubjid,
                'site_code': site_code,
                'notification_type': 'V3_VISIT'
            })
            print(f"NOTIFICATION V3: {usubjid} ({site_code}) - {patient_name} - {appt.V3_EXPECTED_DATE}")
        except Exception as e:
            print(f"Error processing V3 appointment: {e}")
            continue
    
    # === KIỂM TRA V4 APPOINTMENTS (D90) ===
    print(f"NOTIFICATION: Checking V4 appointments for site {site_id}")
    if site_id and site_id != 'all':
        v4_appointments = ExpectedDates.site_objects.filter_by_site(site_id).filter(
            V4_EXPECTED_DATE__gte=today,
            V4_EXPECTED_DATE__lte=upcoming_date,
            V4_EXPECTED_DATE__isnull=False
        ).select_related('USUBJID__USUBJID')
        print(f"NOTIFICATION: Found {v4_appointments.count()} V4 appointments for site {site_id}")
    else:
        v4_appointments = ExpectedDates.objects.filter(
            V4_EXPECTED_DATE__gte=today,
            V4_EXPECTED_DATE__lte=upcoming_date,
            V4_EXPECTED_DATE__isnull=False
        ).select_related('USUBJID__USUBJID')
        print(f"NOTIFICATION: Found {v4_appointments.count()} V4 appointments for ALL sites")

    for appt in v4_appointments:
        try:
            patient_name = 'N/A'
            usubjid = 'N/A'
            site_code = 'N/A'
            
            if hasattr(appt.USUBJID, 'USUBJID') and appt.USUBJID.USUBJID:
                if hasattr(appt.USUBJID.USUBJID, 'INITIAL'):
                    patient_name = appt.USUBJID.USUBJID.INITIAL or 'N/A'
                if hasattr(appt.USUBJID.USUBJID, 'USUBJID'):
                    usubjid = appt.USUBJID.USUBJID.USUBJID or 'N/A'
                    if usubjid and '-' in usubjid:
                        site_code = usubjid.split('-')[0]
                        
            upcoming.append({
                'patient_name': patient_name,
                'expected_date': appt.V4_EXPECTED_DATE,
                'visit_type': 'V4 (D90)',
                'usubjid': usubjid,
                'site_code': site_code,
                'notification_type': 'V4_VISIT'
            })
            print(f"NOTIFICATION V4: {usubjid} ({site_code}) - {patient_name} - {appt.V4_EXPECTED_DATE}")
        except Exception as e:
            print(f"Error processing V4 appointment: {e}")
            continue
    
    # Sắp xếp theo ngày
    upcoming.sort(key=lambda x: x['expected_date'])
    
    # Debug thông tin tổng hợp
    print(f"NOTIFICATION SUMMARY: Total {len(upcoming)} appointments for site {site_id}")
    print(f"NOTIFICATION BREAKDOWN:")
    v2_count = len([x for x in upcoming if x['notification_type'] == 'V2_VISIT'])
    v3_count = len([x for x in upcoming if x['notification_type'] == 'V3_VISIT'])
    v4_count = len([x for x in upcoming if x['notification_type'] == 'V4_VISIT'])
    print(f"  - V2 appointments: {v2_count}")
    print(f"  - V3 appointments: {v3_count}")
    print(f"  - V4 appointments: {v4_count}")
    
    return {
        'upcoming_count': len(upcoming),
        'upcoming_patients': upcoming,
        'site_filtered_notifications': True,  # Flag để template biết đã được lọc
        'notification_site_id': site_id  # Site ID hiện tại cho debug
    }


def study_context(request):
    """Add study-specific context variables to all templates"""
    return {
        'study_folder': 'studies/study_43en',
        'study_code': '43EN',
    }