# backends/api/studies/study_44en/views/views_audit.py
"""
Audit Log Views for Study 44EN
 
Features:
- Advanced filtering (user, action, model, date range, search)
- Pagination
- Integrity verification
- Proper database routing
"""
import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from datetime import datetime
from django.contrib.auth import get_user_model

from backends.audit_log.models.audit_log import AuditLog, AuditLogDetail
from backends.studies.study_44en.utils.permission_decorators import require_crf_view

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
# @require_crf_view('auditlog')
def audit_log_list(request):
    """
    List all audit logs with filters
    
    Permission: view_auditlog
    
    Supports:
    - User filter
    - Action filter (CREATE/UPDATE/VIEW)
    - Model filter
    - Date range filter
    - Full-text search
    - Pagination
    """
    logger.info(f"=== AUDIT LOG LIST (44EN) ===")
    logger.info(f"User: {request.user.username}")
    
    # Get database alias
    study_db = getattr(request, 'study_db_alias', 'db_study_44en')
    
    # Get all logs from study database
    logs = AuditLog.objects.using(study_db).all()
    
    filters = {}
    
    # Filter by user
    user_id = request.GET.get('user', '').strip()
    if user_id:
        try:
            user_id_int = int(user_id)
            logs = logs.filter(user_id=user_id_int)
            filters['user_id'] = user_id
        except ValueError:
            pass
    
    # Filter by action
    action = request.GET.get('action', '').strip()
    if action:
        logs = logs.filter(action=action)
        filters['action'] = action
    
    # Filter by model
    model_name = request.GET.get('model_name', '').strip()
    if model_name:
        logs = logs.filter(model_name=model_name)
        filters['model_name'] = model_name
    
    # Filter by patient ID (HHID or MEMBERID)
    patient_id = request.GET.get('patient_id', '').strip()
    if patient_id:
        logs = logs.filter(patient_id__icontains=patient_id)
        filters['patient_id'] = patient_id
    
    # Filter by date range
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            logs = logs.filter(timestamp__gte=start_dt)
            filters['start_date'] = start_dt
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            logs = logs.filter(timestamp__lte=end_dt)
            filters['end_date'] = end_dt
        except ValueError:
            pass
    
    # Full-text search
    query = request.GET.get('q', '').strip()
    if query:
        logs = logs.filter(
            Q(username__icontains=query) |
            Q(patient_id__icontains=query) |
            Q(reason__icontains=query) |
            Q(model_name__icontains=query)
        )
        filters['query'] = query
    
    # Order and paginate
    logs = logs.order_by('-timestamp')
    
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    logger.info(f"✅ Found {paginator.count} audit logs")
    
    # Get filter options
    user_ids = AuditLog.objects.using(study_db)\
        .values_list('user_id', flat=True)\
        .distinct()
    
    users = User.objects.using('default')\
        .filter(id__in=list(user_ids))\
        .order_by('username')
    
    actions = AuditLog.objects.using(study_db)\
        .values_list('action', flat=True)\
        .distinct()\
        .order_by('action')
    
    model_names = AuditLog.objects.using(study_db)\
        .values_list('model_name', flat=True)\
        .distinct()\
        .order_by('model_name')
    
    context = {
        'page_obj': page_obj,
        'filters': filters,
        'users': users,
        'actions': list(actions),
        'model_names': list(model_names),
    }
    
    return render(request, 'audit_log/audit_log_list.html', context)


@login_required
# @require_crf_view('auditlog')
def audit_log_detail(request, log_id):
    """
    View detailed audit log with all changes
    
    Permission: view_auditlog
    """
    logger.info(f"=== AUDIT LOG DETAIL (44EN) ===")
    logger.info(f"User: {request.user.username}, Log ID: {log_id}")
    
    log = get_object_or_404(AuditLog, id=log_id)
    
    # Get change details
    details = AuditLogDetail.objects.filter(audit_log=log).order_by('field_name')
    
    changes = []
    for detail in details:
        change = {
            'field': detail.field_name,
            'label': _get_field_label(detail.field_name),
            'old_value': detail.old_value,
            'new_value': detail.new_value,
            'old_display': _format_value_display(detail.old_value),
            'new_display': _format_value_display(detail.new_value),
            'reason': detail.reason,
        }
        changes.append(change)
    
    # Get user information
    user = None
    if log.user_id:
        try:
            user = User.objects.using('default').get(id=log.user_id)
        except User.DoesNotExist:
            pass
    
    # Verify integrity
    is_verified = False
    if hasattr(log, 'verify_integrity'):
        is_verified = log.verify_integrity()
    
    context = {
        'log': log,
        'user': user,
        'changes': changes,
        'is_verified': is_verified,
    }
    
    return render(request, 'audit_log/audit_log_detail.html', context)


def _format_value_display(value):
    """Format value for display"""
    if value is None or value == '':
        return '<em class="text-muted">Trống</em>'
    
    if str(value).lower() == 'true':
        return '<span class="badge badge-success">Có</span>'
    if str(value).lower() == 'false':
        return '<span class="badge badge-secondary">Không</span>'
    
    # Handle dates
    if isinstance(value, str) and len(value) == 10:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass
    
    value_str = str(value)
    if len(value_str) > 100:
        return f'{value_str[:100]}...'
    
    return value_str


def _get_field_label(field_name):
    """Get Vietnamese label for field"""
    common_labels = {
        # Common fields
        'HHID': 'Mã Hộ Gia Đình',
        'MEMBERID': 'Mã Thành Viên',
        'WARD': 'Phường/Xã',
        'CITY': 'Thành Phố',
        'PROVINCE': 'Tỉnh',
        'FIRST_NAME': 'Tên',
        'LAST_NAME': 'Họ',
        'DOB': 'Ngày Sinh',
        'GENDER': 'Giới Tính',
        'INITIALS': 'Tên Viết Tắt',
        
        # Dates
        'INTERVIEW_DATE': 'Ngày Phỏng Vấn',
        'ENROLLMENT_DATE': 'Ngày Đăng Ký',
        'FOLLOWUP_DATE': 'Ngày Theo Dõi',
        'SAMPLE_DATE': 'Ngày Lấy Mẫu',
        
        # Metadata
        'last_modified_by': 'Người Sửa Cuối',
        'last_modified_at': 'Thời Gian Sửa Cuối',
    }
    
    return common_labels.get(field_name, field_name)
