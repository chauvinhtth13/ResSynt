import json
from datetime import date

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date


# Import models
from backends.studies.study_43en.models.audit_log import AuditLog, flatten_formset_data
from backends.tenancy.models import User

# Import utils
from backends.studies.study_43en.utils.audit_log_utils import (
    safe_json_loads, normalize_value, find_reason_and_label
)
from backends.studies.study_43en import models

def get_changes(self):
    """Trả về danh sách các thay đổi giữa dữ liệu cũ và mới, hỗ trợ cấu trúc lồng nhau"""
    changes = []
    old_data = flatten_formset_data(self.old_data) if self.old_data else {}
    new_data = flatten_formset_data(self.new_data) if self.new_data else {}
    all_fields = set(list(old_data.keys()) + list(new_data.keys()))
    reasons_dict = safe_json_loads(self.reasons_json, {})

    for field in all_fields:
        # Bỏ qua các trường khóa ngoại chứa 'USUBJID'
        if 'USUBJID' in field.upper():
            continue
        old_value = old_data.get(field)
        new_value = new_data.get(field)
        # Chuẩn hóa giá trị và kiểm tra thay đổi
        normalized_old = normalize_value(old_value)
        normalized_new = normalize_value(new_value)
        # Bỏ qua nếu cả hai giá trị đều trống hoặc giống nhau
        if normalized_old == normalized_new or (not normalized_old and not normalized_new):
            continue
        reason, label = find_reason_and_label(field, reasons_dict)
        # Chỉ thêm trường nếu có lý do thay đổi hợp lệ
        if reason:
            changes.append({
                'field': field,
                'label': label,
                'old_value': old_value if old_value is not None else '',
                'new_value': new_value if new_value is not None else '',
                'reason': reason
            })
    return changes

@login_required
def audit_log_list(request):
    """Hiển thị danh sách nhật ký hệ thống với bộ lọc"""
    # Lấy site_id từ session để lọc theo site
    site_id = request.session.get('selected_site_id', None)
    print(f"DEBUG - audit_log_list - Using site_id: {site_id}")
    
    # Khởi tạo queryset
    logs = AuditLog.objects.all().order_by('-timestamp')
    total_logs = logs.count()
    print(f"DEBUG - Total AuditLog records in DB: {total_logs}")
    
    # Debug thông tin về SITEID distribution
    siteid_stats = AuditLog.objects.values('SITEID').annotate(count=models.Count('id')).order_by('-count')
    print(f"DEBUG - SITEID distribution: {list(siteid_stats)}")
    
    # Áp dụng site filter nếu có và không phải 'all'
    include_legacy = request.GET.get('include_legacy', False)  # Tham số để admin xem dữ liệu cũ
    
    if site_id and site_id != 'all':
        print(f"DEBUG - Filtering by SITEID: {site_id}, include_legacy: {include_legacy}")
        
        if include_legacy and request.user.is_superuser:
            # Chỉ admin mới có thể xem dữ liệu legacy (bao gồm NULL/rỗng)
            logs = logs.filter(
                models.Q(SITEID=site_id) | 
                models.Q(SITEID__isnull=True) | 
                models.Q(SITEID='') |
                models.Q(patient_id__startswith=f"{site_id}-")
            )
            print(f"DEBUG - Admin mode: Including legacy data")
        else:
            # Chỉ lọc theo SITEID chính xác và pattern trong patient_id
            logs = logs.filter(
                models.Q(SITEID=site_id) | 
                models.Q(patient_id__startswith=f"{site_id}-")
            )
        
        print(f"DEBUG - After SITEID filter, count: {logs.count()}")
        
        # Debug breakdown of filtered results
        filtered_by_siteid = AuditLog.objects.filter(SITEID=site_id).count()
        filtered_by_patient_id = AuditLog.objects.filter(patient_id__startswith=f"{site_id}-").count()
        if include_legacy and request.user.is_superuser:
            filtered_by_null = AuditLog.objects.filter(SITEID__isnull=True).count()
            filtered_by_empty = AuditLog.objects.filter(SITEID='').count()
            print(f"DEBUG - Breakdown: SITEID={site_id}({filtered_by_siteid}), PatientID pattern({filtered_by_patient_id}), NULL({filtered_by_null}), Empty({filtered_by_empty})")
        else:
            print(f"DEBUG - Breakdown: SITEID={site_id}({filtered_by_siteid}), PatientID pattern({filtered_by_patient_id})")
    else:
        print(f"DEBUG - No site filter applied (showing all sites), total count: {logs.count()}")
    
    user_id = request.GET.get('user')
    action = request.GET.get('action')
    model_name = request.GET.get('model_name')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if user_id:
        logs = logs.filter(user_id=user_id)
        print(f"DEBUG - After user filter, count: {logs.count()}")
    
    if action:
        logs = logs.filter(action=action)
        print(f"DEBUG - After action filter, count: {logs.count()}")
    
    if model_name:
        logs = logs.filter(model_name=model_name)
        print(f"DEBUG - After model_name filter, count: {logs.count()}")
    
    if start_date:
        start_date = parse_date(start_date)
        if start_date:
            logs = logs.filter(timestamp__date__gte=start_date)
            print(f"DEBUG - After start_date filter, count: {logs.count()}")
    
    if end_date:
        end_date = parse_date(end_date)
        if end_date:
            logs = logs.filter(timestamp__date__lte=end_date)
            print(f"DEBUG - After end_date filter, count: {logs.count()}")
    
    print(f"DEBUG - Final logs count before pagination: {logs.count()}")
    
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    print(f"DEBUG - Paginator info - Total pages: {paginator.num_pages}, Current page: {page_obj.number}")
    
    users = User.objects.all()
    # Sử dụng cùng một bộ lọc site cho danh sách model_names
    if site_id and site_id != 'all':
        if include_legacy and request.user.is_superuser:
            model_names = AuditLog.objects.filter(
                models.Q(SITEID=site_id) | 
                models.Q(SITEID__isnull=True) | 
                models.Q(SITEID='') |
                models.Q(patient_id__startswith=f"{site_id}-")
            ).values_list('model_name', flat=True).distinct()
        else:
            model_names = AuditLog.objects.filter(
                models.Q(SITEID=site_id) | 
                models.Q(patient_id__startswith=f"{site_id}-")
            ).values_list('model_name', flat=True).distinct()
    else:
        model_names = AuditLog.objects.values_list('model_name', flat=True).distinct()
    
    return render(request, 'study_43en/audit_log_list.html', {
        'page_obj': page_obj,
        'users': users,
        'model_names': model_names,
        'actions': [choice[0] for choice in AuditLog.ACTION_CHOICES],
        'filters': {
            'user_id': user_id,
            'action': action,
            'model_name': model_name,
            'start_date': start_date,
            'end_date': end_date,
        }
    })

@login_required
def audit_log_detail(request, log_id):
    log = get_object_or_404(AuditLog, id=log_id)
    old_data = log.get_old_data_dict()
    new_data = log.get_new_data_dict()
    reasons_dict = safe_json_loads(log.reasons_json, {})
    changes = []
    
    if log.action == 'UPDATE' and old_data and new_data:
        all_fields = set(old_data.keys()) | set(new_data.keys())
        for field in all_fields:
            # Bỏ qua các trường khóa ngoại chứa 'USUBJID'
            if 'USUBJID' in field.upper():
                continue
            old_value = old_data.get(field, '')
            new_value = new_data.get(field, '')
            # Chuẩn hóa giá trị và kiểm tra thay đổi
            normalized_old = normalize_value(old_value)
            normalized_new = normalize_value(new_value)
            # Bỏ qua nếu cả hai giá trị đều trống hoặc giống nhau
            if normalized_old == normalized_new or (not normalized_old and not normalized_new):
                continue
            reason, label = find_reason_and_label(field, reasons_dict)
            # Chỉ thêm trường nếu có lý do thay đổi hợp lệ
            if reason:
                changes.append({
                    'field': field,
                    'label': label,
                    'old_value': old_value if old_value is not None else '',
                    'new_value': new_value if new_value is not None else '',
                    'reason': reason
                })
    
    return render(request, 'study_43en/audit_log_detail.html', {
        'log': log,
        'changes': changes,
        'old_data': old_data,
        'new_data': new_data,
    })