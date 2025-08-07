# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import login_required
# from study_43en.models import ScreeningCase, EnrollmentCase, SampleCollection, ScreeningContact, EnrollmentContact
# from django.db.models import Count, Q
# from datetime import datetime, timedelta
# import logging

# logger = logging.getLogger(__name__)

# def custom_404(request, exception):
#     return render(request, '404.html', status=404)

# @login_required
# def admin_dashboard(request):
#     """
#     Dashboard chính cho quản lý bệnh nhân, bổ sung thông báo ngày expected sắp tới.
#     """
#     from datetime import date, timedelta
#     from study_43en.models import ExpectedDates, EnrollmentCase

#     try:
#         # Tổng số bệnh nhân và người tiếp xúc
#         total_patients = ScreeningCase.objects.count()
#         screening_patients = ScreeningCase.objects.count()
#         enrolled_patients = ScreeningCase.objects.filter(
#             UPPER16AGE=True,
#             INFPRIOR2OR48HRSADMIT=True,
#             ISOLATEDKPNFROMINFECTIONORBLOOD=True,
#             KPNISOUNTREATEDSTABLE=False,
#             CONSENTTOSTUDY=True
#         ).count()

#         # Tính phần trăm so với mục tiêu 750
#         percent_target = round(enrolled_patients / 750 * 100, 1) if enrolled_patients else 0

#         total_contacts = ScreeningContact.objects.count()
#         screening_contacts = ScreeningContact.objects.count()
#         enrolled_contacts = EnrollmentContact.objects.count()

#         # Tổng hợp lý do không tham gia nghiên cứu (Patient)
#         patient_reasons = (
#             ScreeningCase.objects
#             .filter(CONSENTTOSTUDY=False)
#             .exclude(UNRECRUITED_REASON__isnull=True)
#             .exclude(UNRECRUITED_REASON__exact='')
#             .values('UNRECRUITED_REASON')
#             .annotate(count=Count('*'))
#             .order_by('-count')
#         )

#         contact_reasons = (
#             ScreeningContact.objects
#             .exclude(UNRECRUITED_REASON__isnull=True)
#             .exclude(UNRECRUITED_REASON__exact='')
#             .values('UNRECRUITED_REASON')
#             .annotate(count=Count('screening_id'))
#             .order_by('-count')
#         )

#         # Lấy ngày bắt đầu dự án (ngày nhỏ nhất ENRDATE)
#         first_enr = EnrollmentCase.objects.order_by('ENRDATE').values_list('ENRDATE', flat=True).first()
#         project_start = first_enr if first_enr else None

#         # Lấy danh sách expected date sắp tới (trong 3 ngày tới)
#         today = date.today()
#         soon = today + timedelta(days=3)
#         upcoming_expected = ExpectedDates.objects.filter(
#             d10_expected_date__range=[today, soon]
#         ).select_related('enrollment_case')

#         context = {
#             'total_patients': total_patients,
#             'screening_patients': screening_patients,
#             'enrolled_patients': enrolled_patients,
#             'total_contacts': total_contacts,
#             'screening_contacts': screening_contacts,
#             'enrolled_contacts': enrolled_contacts,
#             'patient_reasons': add_percent_to_reasons(patient_reasons),
#             'contact_reasons': add_percent_to_reasons(contact_reasons),
#             'upcoming_expected': upcoming_expected,
#             'upcoming_expected_count': upcoming_expected.count(),
#             'percent_target': percent_target,
#             'project_start': project_start,
#             'today': today,
#         }

#         return render(request, 'admin_dashboard.html', context)

#     except Exception as e:
#         logger.error(f"Error in admin_dashboard view: {str(e)}")
#         return render(request, 'admin_dashboard.html',{'error': str(e)})
    
# @login_required
# def patient_statistics(request):
#     """
#     Trang thống kê chi tiết về bệnh nhân 43EN
#     """
#     try:
#         # Thống kê cơ bản
#         total_screening = ScreeningCase.objects.count()
#         total_enrolled = EnrollmentCase.objects.count()
#         total_contacts = ScreeningContact.objects.count()
#         total_contact_enrolled = EnrollmentContact.objects.count()
        
#         # Thống kê theo thời gian (6 tháng gần đây)
#         six_months_ago = datetime.now() - timedelta(days=180)
        
#         # Bệnh nhân sàng lọc theo tháng
#         screening_by_month = ScreeningCase.objects.filter(
#             SCREENINGFORMDATE__gte=six_months_ago
#         ).extra(
#             select={'month': "EXTRACT(month FROM SCREENINGFORMDATE)"}
#         ).values('month').annotate(count=Count('USUBJID')).order_by('month')
        
#         # Bệnh nhân tham gia theo tháng
#         enrolled_by_month = EnrollmentCase.objects.filter(
#             ENRDATE__gte=six_months_ago
#         ).extra(
#             select={'month': "EXTRACT(month FROM ENRDATE)"}
#         ).values('month').annotate(count=Count('USUBJID')).order_by('month')
        
#         # Thống kê theo giới tính
#         gender_stats = EnrollmentCase.objects.values('SEX').annotate(
#             count=Count('USUBJID')
#         ).exclude(SEX__isnull=True)
        
#         # Thống kê theo độ tuổi
#         age_stats = {
#             'under_18': EnrollmentCase.objects.filter(AGEIFDOBUNKNOWN__lt=18).count(),
#             '18_30': EnrollmentCase.objects.filter(AGEIFDOBUNKNOWN__gte=18, AGEIFDOBUNKNOWN__lt=30).count(),
#             '30_50': EnrollmentCase.objects.filter(AGEIFDOBUNKNOWN__gte=30, AGEIFDOBUNKNOWN__lt=50).count(),
#             '50_70': EnrollmentCase.objects.filter(AGEIFDOBUNKNOWN__gte=50, AGEIFDOBUNKNOWN__lt=70).count(),
#             'over_70': EnrollmentCase.objects.filter(AGEIFDOBUNKNOWN__gte=70).count(),
#         }
        
#         # Thống kê contact
#         contact_stats = {
#             'total_screened': ScreeningContact.objects.count(),
#             'eligible': ScreeningContact.objects.filter(
#                 CONSENTTOSTUDY=True,
#                 LIVEIN5DAYS3MTHS=True,
#                 MEALCAREONCEDAY=True
#             ).count(),
#             'enrolled': EnrollmentContact.objects.count(),
#         }
        
#         # Tính tỷ lệ phần trăm
#         patient_enrollment_rate = (total_enrolled / total_screening * 100) if total_screening > 0 else 0
#         contact_enrollment_rate = (total_contact_enrolled / total_contacts * 100) if total_contacts > 0 else 0
        
#         context = {
#             'total_screening': total_screening,
#             'total_enrolled': total_enrolled,
#             'total_contacts': total_contacts,
#             'total_contact_enrolled': total_contact_enrolled,
#             'patient_enrollment_rate': round(patient_enrollment_rate, 1),
#             'contact_enrollment_rate': round(contact_enrollment_rate, 1),
#             'screening_by_month': list(screening_by_month),
#             'enrolled_by_month': list(enrolled_by_month),
#             'gender_stats': list(gender_stats),
#             'age_stats': age_stats,
#             'contact_stats': contact_stats,
#         }
        
#         return render(request, 'patient_statistics.html', context)
        
#     except Exception as e:
#         logger.error(f"Error in patient_statistics view: {str(e)}")
#         return render(request, 'patient_statistics.html', {'error': str(e)})
       
# @login_required
# def select_study(request):
#     """
#     View for redirecting to 43EN study.
#     This is kept for backwards compatibility, but can also show some statistics.
#     """
#     # Có thể hiển thị một số thông tin thống kê về 43EN study
#     total_patients = ScreeningCase.objects.count()
#     eligible_patients = EnrollmentCase.objects.count() 
    
#     context = {
#         'total_patients': total_patients,
#         'eligible_patients': eligible_patients
#     }
    
#     # Bây giờ hiển thị trang select_study với thông tin 43EN
#     return render(request, 'select_study.html', context)
    
#     # Nếu muốn chuyển hướng trực tiếp đến 43EN, uncomment dòng dưới
#     # return redirect('43en:screening_case_list')  # URL cho study_43en


# def add_percent_to_reasons(reason_qs):
#     """
#     Nhận vào queryset lý do (có trường 'count'), trả về list dict có thêm 'percent'
#     """
#     reasons = list(reason_qs)
#     total = sum(r['count'] for r in reasons)
#     for r in reasons:
#         r['percent'] = round((r['count'] / total * 100), 1) if total > 0 else 0
#     return reasons