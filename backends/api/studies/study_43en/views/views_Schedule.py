import logging
from datetime import date, datetime, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils.translation import gettext as _

# Import models từ study app
from backends.studies.study_43en.models.patient import (
    FollowUpCase, FollowUpCase90,

)
from backends.studies.study_43en.models.contact import (
    ContactFollowUp28, ContactFollowUp90
)
from backends.studies.study_43en.models.schedule import (
    FollowUpStatus
)





# Import utils từ study app

logger = logging.getLogger(__name__)


from django.http import HttpResponse
from openpyxl import Workbook
from django.http import HttpResponse
from django.utils.timezone import localtime
from openpyxl.styles import Font, PatternFill


@login_required
def followup_tracking_list(request):
    """Hiển thị danh sách theo dõi lịch hẹn bệnh nhân và người tiếp xúc"""
    # Lấy ngày hiện tại
    today = date.today()
    
    # Tính ngày đầu và cuối tuần hiện tại (từ thứ 2 đến chủ nhật)
    day_of_week = today.weekday()  # 0 = Monday, 6 = Sunday
    start_of_week = today - timedelta(days=day_of_week)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Lọc theo ngày
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Nếu không có date_from và date_to, mặc định hiển thị lịch hẹn trong tuần này
    if not date_from and not date_to:
        date_from = start_of_week
        date_to = end_of_week
    else:
        # Parse date_from và date_to nếu có
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None
        except ValueError:
            date_from = start_of_week
            date_to = end_of_week
    
    # Lọc theo tham số khác
    visit_filter = request.GET.get('visit')
    status_filter = request.GET.get('status')
    subject_type_filter = request.GET.get('subject_type')
    search_query = request.GET.get('search')
    
    # Lấy site_id từ session
    site_id = request.session.get('selected_site_id')
    
    # Query cơ bản
    if site_id:
        followups = FollowUpStatus.site_objects.filter_by_site(site_id)
    else:
        followups = FollowUpStatus.objects.all()
    
    # Áp dụng filter theo khoảng ngày
    if date_from:
        followups = followups.filter(Q(EXPECTED_DATE__gte=date_from) | 
                                   Q(EXPECTED_FROM__gte=date_from) |
                                   Q(ACTUAL_DATE__gte=date_from))
    if date_to:
        followups = followups.filter(Q(EXPECTED_DATE__lte=date_to) | 
                                   Q(EXPECTED_TO__lte=date_to) |
                                   Q(ACTUAL_DATE__lte=date_to))
    
    # Áp dụng các bộ lọc khác
    if visit_filter:
        followups = followups.filter(VISIT=visit_filter)
    
    if status_filter:
        followups = followups.filter(STATUS=status_filter)
    
    if subject_type_filter:
        followups = followups.filter(SUBJECT_TYPE=subject_type_filter)
    
    if search_query:
        followups = followups.filter(
            Q(USUBJID__icontains=search_query) | 
            Q(INITIAL__icontains=search_query) |
            Q(PHONE__icontains=search_query)
        )
    
    # Sắp xếp ưu tiên: trễ hẹn -> sắp tới -> không hoàn thành -> hoàn thành
    followups = followups.order_by(
        Case(
            When(STATUS='LATE', then=Value(0)),
            When(STATUS='UPCOMING', then=Value(1)),
            When(STATUS='MISSED', then=Value(2)),
            When(STATUS='COMPLETED', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        ),
        'EXPECTED_DATE'
    )
    
    # Thống kê
    total_appointments = followups.count()
    completed_count = followups.filter(STATUS='COMPLETED').count()
    late_count = followups.filter(STATUS='LATE').count()
    missed_count = followups.filter(STATUS='MISSED').count()
    
    # Phân trang
    paginator = Paginator(followups, 15)
    page = request.GET.get('page', 1)
    
    try:
        followups_page = paginator.page(page)
    except PageNotAnInteger:
        followups_page = paginator.page(1)
    except EmptyPage:
        followups_page = paginator.page(paginator.num_pages)
    
    # Thống kê chi tiết theo đối tượng và lần thăm
    upcoming_stats = {
        'PATIENT': {'V2': 0, 'V3': 0, 'V4': 0, 'total': 0},
        'CONTACT': {'V2': 0, 'V3': 0, 'V4': 0, 'total': 0}
    }
    
    upcoming_date = datetime.now().date() + timedelta(days=7)
    
    # Áp dụng site filtering cho upcoming_followups
    if site_id:
        upcoming_followups = FollowUpStatus.site_objects.filter_by_site(site_id).filter(
            STATUS='UPCOMING',
            EXPECTED_DATE__lte=upcoming_date
        )
    else:
        upcoming_followups = FollowUpStatus.objects.filter(
            STATUS='UPCOMING',
            EXPECTED_DATE__lte=upcoming_date
        )
    
    for followup in upcoming_followups:
        upcoming_stats[followup.SUBJECT_TYPE][followup.VISIT] = upcoming_stats[followup.SUBJECT_TYPE].get(followup.VISIT, 0) + 1
        upcoming_stats[followup.SUBJECT_TYPE]['total'] = upcoming_stats[followup.SUBJECT_TYPE].get('total', 0) + 1
    
    # Thống kê lịch hẹn trễ
    late_stats = {
        'PATIENT': {'V2': 0, 'V3': 0, 'V4': 0, 'total': 0},
        'CONTACT': {'V2': 0, 'V3': 0, 'V4': 0, 'total': 0}
    }
    
    # Áp dụng site filtering cho late_followups
    if site_id:
        late_followups = FollowUpStatus.site_objects.filter_by_site(site_id).filter(STATUS='LATE')
    else:
        late_followups = FollowUpStatus.objects.filter(STATUS='LATE')
    
    for followup in late_followups:
        late_stats[followup.SUBJECT_TYPE][followup.VISIT] = late_stats[followup.SUBJECT_TYPE].get(followup.VISIT, 0) + 1
        late_stats[followup.SUBJECT_TYPE]['total'] = late_stats[followup.SUBJECT_TYPE].get('total', 0) + 1
    
    context = {
        'followups': followups_page,
        'visit_choices': FollowUpStatus.VISIT_CHOICES,
        'status_choices': FollowUpStatus.STATUS_CHOICES,
        'subject_type_choices': FollowUpStatus.SUBJECT_TYPE_CHOICES,
        'current_visit': visit_filter,
        'current_status': status_filter,
        'current_subject_type': subject_type_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'upcoming_stats': upcoming_stats,
        'late_stats': late_stats,
        'total_appointments': total_appointments,
        'completed_count': completed_count,
        'late_count': late_count,
        'missed_count': missed_count,
    }
    
    return render(request, 'studies/study_43en/CRF/followup_tracking_list.html', context)

@login_required
def update_followup_status(request, pk):
    """Cập nhật trạng thái theo dõi"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Chỉ hỗ trợ phương thức POST'})
    
    try:
        followup = FollowUpStatus.objects.get(pk=pk)
        
        # Cập nhật từ form
        actual_date = request.POST.get('actual_date')
        status = request.POST.get('status')
        notes = request.POST.get('notes')
        
        if actual_date:
            followup.ACTUAL_DATE = datetime.strptime(actual_date, '%Y-%m-%d').date()
            
            # Cập nhật form tương ứng nếu có
            if followup.SUBJECT_TYPE == 'PATIENT':
                if followup.VISIT == 'V3':
                    try:
                        fu_case = FollowUpCase.objects.get(USUBJID_id=followup.USUBJID)
                        fu_case.ASSESSDATE = followup.ACTUAL_DATE
                        fu_case.save(update_fields=['ASSESSDATE'])
                    except FollowUpCase.DoesNotExist:
                        pass
                        
                elif followup.VISIT == 'V4':
                    try:
                        fu_case = FollowUpCase90.objects.get(USUBJID_id=followup.USUBJID)
                        fu_case.ASSESSDATE = followup.ACTUAL_DATE
                        fu_case.save(update_fields=['ASSESSDATE'])
                    except FollowUpCase90.DoesNotExist:
                        pass
            
            elif followup.SUBJECT_TYPE == 'CONTACT':
                if followup.VISIT == 'V2':
                    try:
                        fu_case = ContactFollowUp28.objects.get(USUBJID_id=followup.USUBJID)
                        fu_case.ASSESSDATE = followup.ACTUAL_DATE
                        fu_case.save(update_fields=['ASSESSDATE'])
                    except ContactFollowUp28.DoesNotExist:
                        pass
                        
                elif followup.VISIT == 'V3':
                    try:
                        fu_case = ContactFollowUp90.objects.get(USUBJID_id=followup.USUBJID)
                        fu_case.ASSESSDATE = followup.ACTUAL_DATE
                        fu_case.save(update_fields=['ASSESSDATE'])
                    except ContactFollowUp90.DoesNotExist:
                        pass
            
        if status:
            followup.STATUS = status
            
        if notes:
            followup.NOTES = notes
            
        followup.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Đã cập nhật thành công',
            'status': followup.get_STATUS_display(),
            'actual_date': followup.ACTUAL_DATE.strftime('%d/%m/%Y') if followup.ACTUAL_DATE else None
        })
        
    except FollowUpStatus.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy bản ghi'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    

@login_required
def export_followup_tracking(request):
    """Xuất danh sách theo dõi lịch hẹn ra Excel"""
    # Lấy các tham số tương tự như trong view followup_tracking_list
    visit_filter = request.GET.get('visit')
    status_filter = request.GET.get('status')
    subject_type_filter = request.GET.get('subject_type')
    search_query = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Query cơ bản
    followups = FollowUpStatus.objects.all()
    
    # Áp dụng filter theo khoảng ngày
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            followups = followups.filter(Q(EXPECTED_DATE__gte=date_from) | 
                                       Q(EXPECTED_FROM__gte=date_from) |
                                       Q(ACTUAL_DATE__gte=date_from))
        except ValueError:
            pass
            
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            followups = followups.filter(Q(EXPECTED_DATE__lte=date_to) | 
                                       Q(EXPECTED_TO__lte=date_to) |
                                       Q(ACTUAL_DATE__lte=date_to))
        except ValueError:
            pass
    
    # Áp dụng các bộ lọc
    if visit_filter:
        followups = followups.filter(VISIT=visit_filter)
    
    if status_filter:
        followups = followups.filter(STATUS=status_filter)
    
    if subject_type_filter:
        followups = followups.filter(SUBJECT_TYPE=subject_type_filter)
    
    if search_query:
        followups = followups.filter(
            Q(USUBJID__icontains=search_query) | 
            Q(INITIAL__icontains=search_query)
        )
    
    # Sắp xếp
    followups = followups.order_by(
        Case(
            When(STATUS='LATE', then=Value(0)),
            When(STATUS='UPCOMING', then=Value(1)),
            When(STATUS='MISSED', then=Value(2)),
            When(STATUS='COMPLETED', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        ),
        'EXPECTED_DATE'
    )
    
    # Tạo workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sách theo dõi"
    
    # Thêm header
    headers = [
        'STT', 'USUBJID', 'Tên viết tắt', 'Loại đối tượng', 'Lần thăm', 
        'Ngày dự kiến', 'Khoảng thời gian', 'Ngày thực tế', 'Trạng thái', 'SĐT'
    ]
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    # Thêm dữ liệu
    status_map = dict(FollowUpStatus.STATUS_CHOICES)
    subject_type_map = dict(FollowUpStatus.SUBJECT_TYPE_CHOICES)
    visit_map = dict(FollowUpStatus.VISIT_CHOICES)
    
    for row_num, followup in enumerate(followups, 2):
        ws.cell(row=row_num, column=1, value=row_num-1)
        ws.cell(row=row_num, column=2, value=followup.USUBJID)
        ws.cell(row=row_num, column=3, value=followup.INITIAL)
        ws.cell(row=row_num, column=4, value=subject_type_map.get(followup.SUBJECT_TYPE, followup.SUBJECT_TYPE))
        ws.cell(row=row_num, column=5, value=visit_map.get(followup.VISIT, followup.VISIT))
        
        if followup.EXPECTED_DATE:
            ws.cell(row=row_num, column=6, value=followup.EXPECTED_DATE)
        
        expected_range = ""
        if followup.EXPECTED_FROM and followup.EXPECTED_TO:
            expected_range = f"{followup.EXPECTED_FROM.strftime('%d/%m/%Y')} - {followup.EXPECTED_TO.strftime('%d/%m/%Y')}"
        ws.cell(row=row_num, column=7, value=expected_range)
        
        if followup.ACTUAL_DATE:
            ws.cell(row=row_num, column=8, value=followup.ACTUAL_DATE)
        
        ws.cell(row=row_num, column=9, value=status_map.get(followup.STATUS, followup.STATUS))
        ws.cell(row=row_num, column=10, value=followup.PHONE)
    
    # Tự động điều chỉnh chiều rộng cột
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width
    
    # Tạo response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=theo_doi_lich_hen_{localtime().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    wb.save(response)
    return response