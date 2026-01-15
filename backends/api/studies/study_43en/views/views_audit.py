# backends/studies/study_43en/views/views_audit.py
"""
Audit Log Views - List and Detail with Site Filtering
 
Features:
- Site-based access control (all/single/multiple)
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

from backends.studies.study_43en.models import AuditLog, AuditLogDetail
from backends.audit_logs.utils.permission_decorators import require_crf_view
from backends.studies.study_43en.utils.site_utils import get_site_filter_params

# Explicit database alias for reliable routing
DB_ALIAS = 'db_study_43en'

User = get_user_model()
logger = logging.getLogger(__name__)


# ==========================================
# LIST VIEW
# ==========================================

@login_required
@require_crf_view('AuditLog', redirect_to='study_43en:home_dashboard')
def audit_log_list(request):
    """
    List all audit logs with filters and site-based access control
    
    Permission: view_auditlog
    
    Supports:
    - Site filtering (all/single/multiple)
    - User filter
    - Action filter (CREATE/UPDATE/DELETE/VIEW)
    - Model filter
    - Patient ID search
    - Date range filter
    - Full-text search
    - Pagination
    """
    logger.info(f"=== AUDIT LOG LIST ===")
    logger.info(f"User: {request.user.username}")
    filters = {}
    
    # ==========================================
    # 1. APPLY SITE FILTERING
    # ==========================================
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f" Site filter: {site_filter}, Type: {filter_type}")
    
    # Get filtered queryset with explicit database routing
    # NOTE: AuditLog doesn't have site_objects manager, so we filter SITEID directly
    if filter_type == 'all':
        logs = AuditLog.objects.using(DB_ALIAS).all()
    elif filter_type == 'single':
        logs = AuditLog.objects.using(DB_ALIAS).filter(SITEID=site_filter)
    elif filter_type == 'multiple':
        if site_filter:
            logs = AuditLog.objects.using(DB_ALIAS).filter(SITEID__in=site_filter)
        else:
            logs = AuditLog.objects.using(DB_ALIAS).none()
    else:
        logs = AuditLog.objects.using(DB_ALIAS).all()
    
    # ==========================================
    # 3. APPLY USER FILTERS
    # ==========================================
    study_code = getattr(request, 'study_code', '').lower()
    
    # Filter by user
    user_id = request.GET.get('user', '').strip()
    if user_id:
        try:
            user_id_int = int(user_id)
            logs = logs.filter(user_id=user_id_int)
            filters['user_id'] = user_id
            logger.debug(f"Filter by user: {user_id_int}")
        except ValueError:
            logger.warning(f"Invalid user_id: {user_id}")
    
    # Filter by action
    action = request.GET.get('action', '').strip()
    if action:
        logs = logs.filter(action=action)
        filters['action'] = action
        logger.debug(f"Filter by action: {action}")
    
    # Filter by model
    model_name = request.GET.get('model_name', '').strip()
    if model_name:
        logs = logs.filter(model_name=model_name)
        filters['model_name'] = model_name
        logger.debug(f"Filter by model: {model_name}")
    
    # Filter by patient ID
    patient_id = request.GET.get('patient_id', '').strip()
    if patient_id:
        logs = logs.filter(patient_id__icontains=patient_id)
        filters['patient_id'] = patient_id
        logger.debug(f"Filter by patient: {patient_id}")
    
    # Filter by date range
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            logs = logs.filter(timestamp__gte=start_dt)
            filters['start_date'] = start_dt
            logger.debug(f"Filter from date: {start_dt}")
        except ValueError:
            logger.warning(f"Invalid start_date: {start_date_str}")
    
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            # Include entire end day (23:59:59)
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            logs = logs.filter(timestamp__lte=end_dt)
            filters['end_date'] = end_dt
            logger.debug(f"Filter to date: {end_dt}")
        except ValueError:
            logger.warning(f"Invalid end_date: {end_date_str}")
    
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
        logger.debug(f"Search query: {query}")
    
    # ==========================================
    # 4. ORDER AND PAGINATE
    # ==========================================
    logs = logs.order_by('-timestamp')
    
    paginator = Paginator(logs, 25)  # 25 logs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    logger.info(f" Found {paginator.count} audit logs, showing page {page_obj.number}/{paginator.num_pages}")
    
    # ==========================================
    # 5. GET FILTER OPTIONS (DISTINCT & SORTED)
    # ==========================================
    
    # Get unique user_ids from audit logs (with explicit DB routing)
    user_ids = AuditLog.objects.using(DB_ALIAS)\
        .values_list('user_id', flat=True)\
        .distinct()
    
    # Query users from management DB
    users = User.objects.using('default')\
        .filter(id__in=list(user_ids))\
        .order_by('username')
    
    # Get unique actions (sorted) - with explicit DB routing
    actions = AuditLog.objects.using(DB_ALIAS)\
        .values_list('action', flat=True)\
        .distinct()\
        .order_by('action')
    
    # Get unique model names (sorted) - with explicit DB routing
    model_names = AuditLog.objects.using(DB_ALIAS)\
        .values_list('model_name', flat=True)\
        .distinct()\
        .order_by('model_name')
    
    logger.info(f" Filter options: {len(users)} users, {len(actions)} actions, {len(model_names)} models")
    
    # ==========================================
    # 6. RENDER TEMPLATE
    # ==========================================
    study_code = getattr(request, 'study_code', '43en')
    context = {
        'page_obj': page_obj,
        'filters': filters,
        'users': users,
        'actions': list(actions),        #  Convert to list
        'model_names': list(model_names), #  Convert to list
        'site_filter': site_filter,
        'filter_type': filter_type,
        'study_code': study_code,
    }
    
    return render(request, 'audit_log/audit_log_list.html', context)


# ==========================================
# DETAIL VIEW
# ==========================================

@login_required
@require_crf_view('AuditLog', redirect_to='study_43en:audit_log_list')
def audit_log_detail(request, log_id):
    """
    View detailed audit log with all changes and integrity verification
    
    Permission: view_auditlog
    
    Features:
    - Site-based access control
    - Change details with field labels
    - Integrity verification (checksum)
    - User information
    """
    logger.info(f"=== AUDIT LOG DETAIL ===")
    logger.info(f"User: {request.user.username}, Log ID: {log_id}")
    
    # ==========================================
    # 1. GET AUDIT LOG
    # ==========================================
    # Use explicit database routing
    try:
        log = AuditLog.objects.using(DB_ALIAS).get(id=log_id)
    except AuditLog.DoesNotExist:
        messages.error(request, 'Audit log không tồn tại!')
        return redirect('study_43en:audit_log_list')
    
    logger.info(f"📄 Log: {log.action} on {log.model_name} by {log.username}")
    
    # ==========================================
    # 2. CHECK SITE ACCESS
    # ==========================================
    site_filter, filter_type = get_site_filter_params(request)
    
    # Verify user has access to this log's site
    if filter_type == 'single':
        # Single site user - must match exactly
        if log.SITEID != site_filter:
            logger.warning(
                f"🚫 Access denied: User site={site_filter}, Log site={log.SITEID}"
            )
            messages.error(request, 'Bạn không có quyền xem audit log này!')
            return redirect('study_43en:audit_log_list')
    
    elif filter_type == 'multiple':
        # Multi-site user - must be in allowed sites
        if log.SITEID not in site_filter:
            logger.warning(
                f"🚫 Access denied: User sites={site_filter}, Log site={log.SITEID}"
            )
            messages.error(request, 'Bạn không có quyền xem audit log này!')
            return redirect('study_43en:audit_log_list')
    
    # If filter_type == 'all': Super admin can access everything
    logger.info(f" Site access verified")
    
    # ==========================================
    # 3. GET CHANGE DETAILS
    # ==========================================
    details = AuditLogDetail.objects.using(DB_ALIAS).filter(audit_log=log).order_by('field_name')
    
    changes = []
    for detail in details:
        # Generate display_name for formset fields
        display_name = _generate_formset_display_name(detail.field_name, log.model_name)
        
        change = {
            'field': detail.field_name,
            'label': _get_field_label(log.model_name, detail.field_name),
            'display_name': display_name,  # 🆕 Add display_name
            'old_value': detail.old_value,
            'new_value': detail.new_value,
            'old_display': _format_value_display(detail.old_value),
            'new_display': _format_value_display(detail.new_value),
            'reason': detail.reason,
        }
        changes.append(change)
    
    logger.info(f" Found {len(changes)} field changes")
    
    # ==========================================
    # 4. GET USER INFORMATION
    # ==========================================
    user = None
    if hasattr(log, 'get_user') and callable(log.get_user):
        user = log.get_user()
    elif log.user_id:
        try:
            user = User.objects.using('default').get(id=log.user_id)
        except User.DoesNotExist:
            logger.warning(f"⚠️ User {log.user_id} not found")
    
    # ==========================================
    # 5. VERIFY INTEGRITY
    # ==========================================
    is_verified = False
    if hasattr(log, 'verify_integrity') and callable(log.verify_integrity):
        is_verified = log.verify_integrity()
    
    if not is_verified:
        logger.warning(f"🚨 INTEGRITY CHECK FAILED for audit log {log_id}")
    else:
        logger.info(f" Integrity verified")
    
    # ==========================================
    # 6. RENDER TEMPLATE
    # ==========================================
    context = {
        'log': log,
        'user': user,
        'changes': changes,
        'is_verified': is_verified,
        'site_filter': site_filter,
        'filter_type': filter_type,
        'study_code': getattr(request, 'study_code', '43en'),  # Dynamic study code from middleware
    }
    
    return render(request, 'audit_log/audit_log_detail.html', context)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _generate_formset_display_name(field_name: str, model_name: str) -> str:
    """
    Generate human-readable display name for formset field changes
    
    Args:
        field_name: Technical field name like "laboratory_tests_2163_RESULT" or "test_539_MIC"
        model_name: Model name like "LABORATORYTEST" or "ANTIBIOTICSENSITIVITY"
        
    Returns:
        Human-readable name like "Eosinophils - Kết quả" or "003-A-001-C3-AMP - MIC"
    """
    # Check if this is a formset field (contains underscore and pk)
    parts = field_name.split('_')
    
    # Pattern 1: test_pk_FIELDNAME (e.g., test_539_MIC for antibiotic)
    # Pattern 2: formset_name_pk_FIELDNAME (e.g., laboratory_tests_2163_RESULT)
    if len(parts) < 3:
        return None
    
    # Try to extract pk and field name
    try:
        # Special case: "test_539_MIC" pattern for antibiotic sensitivity
        if parts[0] == 'test' and len(parts) >= 3 and parts[1].isdigit():
            pk = parts[1]
            actual_field = '_'.join(parts[2:])
        else:
            # General case: Find the pk (should be numeric)
            pk_index = None
            for i, part in enumerate(parts):
                if part.isdigit():
                    pk_index = i
                    break
            
            if pk_index is None:
                return None
            
            # Extract actual field name (everything after pk)
            actual_field = '_'.join(parts[pk_index + 1:])
            pk = parts[pk_index]
        
        # Map field names to Vietnamese labels
        field_labels = {
            'RESULT': 'Kết quả',
            'PERFORMED': 'Đã thực hiện',
            'PERFORMEDDATE': 'Ngày thực hiện',
            'DRUGNAME': 'Tên thuốc',
            'ICDCODE': 'Mã ICD',
            'SPECIMENTYPE': 'Loại mẫu',
            'SENSITIVITY_LEVEL': 'LEVEL',
            'IZDIAM': 'Zone Diameter',
            'MIC': 'MIC',
        }
        
        field_label = field_labels.get(actual_field, actual_field)
        
        # Try to get instance name based on model
        if model_name in ('ANTIBIOTICSENSITIVITY', 'ANTIBIOTIC_SENSITIVITY'):
            try:
                from backends.studies.study_43en.models.patient import AntibioticSensitivity
                test = AntibioticSensitivity.objects.get(pk=int(pk))
                ast_id = test.AST_ID if hasattr(test, 'AST_ID') else str(test)
                return f"{ast_id} - {field_label}"
            except Exception as e:
                logger.warning(f"Failed to get AntibioticSensitivity {pk}: {e}")
                return None
        
        elif model_name == 'LABORATORYTEST':
            try:
                from backends.studies.study_43en.models.patient import LaboratoryTest
                test = LaboratoryTest.objects.get(pk=int(pk))
                test_name = test.get_TESTTYPE_display() if hasattr(test, 'get_TESTTYPE_display') else str(test)
                return f"{test_name} - {field_label}"
            except Exception as e:
                logger.warning(f"Failed to get LaboratoryTest {pk}: {e}")
                return None
        
        # Add more model types as needed
        # elif model_name == 'OTHER_MODEL':
        #     ...
        
    except Exception as e:
        logger.warning(f"Failed to generate display name for {field_name}: {e}")
    
    return None


def _format_value_display(value):
    """
    Format value for display in template
    
    Args:
        value: Raw field value
    
    Returns:
        str: HTML-formatted display value
    """
    # Handle None/empty
    if value is None or value == '':
        return '<em class="text-muted">Trống</em>'
    
    # Handle boolean strings
    if str(value).lower() == 'true':
        return '<span class="badge badge-success">Có</span>'
    if str(value).lower() == 'false':
        return '<span class="badge badge-secondary">Không</span>'
    
    # Handle dates (ISO format)
    if isinstance(value, str) and len(value) == 10:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass
    
    # Truncate long values
    value_str = str(value)
    if len(value_str) > 100:
        return f'{value_str[:100]}...'
    
    return value_str


def _get_field_label(model_name, field_name):
    """
    Get human-readable Vietnamese label for field
    
    Args:
        model_name: Model name (e.g., 'SCREENINGCASE')
        field_name: Field name (e.g., 'SCREENINGFORMDATE')
    
    Returns:
        str: Vietnamese field label
    """
    # ==========================================
    # COMMON FIELDS (ALL MODELS)
    # ==========================================
    common_labels = {
        # IDs
        'SCRID': 'Mã Screening',
        'USUBJID': 'Mã Bệnh Nhân',
        'SUBJID': 'Mã Subject',
        'STUDYID': 'Mã Nghiên Cứu',
        'SITEID': 'Mã Cơ Sở',
        
        # Metadata
        'INITIAL': 'Tên Viết Tắt',
        'ENTRY': 'Người Nhập',
        'ENTEREDTIME': 'Thời Gian Nhập',
        'version': 'Phiên Bản',
        'last_modified_by': 'Người Sửa Cuối',
        'last_modified_at': 'Thời Gian Sửa Cuối',
        
        # Dates
        'SCREENINGFORMDATE': 'Ngày Screening',
        'ENRDATE': 'Ngày Enrollment',
        'DISCHARGEDATE': 'Ngày Xuất Viện',
        'FOLLOWUPDATE': 'Ngày Follow-up',
        'SAMPLEDATE': 'Ngày Lấy Mẫu',
        'EvaluateDate': 'Ngày Đánh Giá',
        'DeathDate': 'Ngày Tử Vong',
        
        # Screening fields
        'UPPER16AGE': 'Trên 16 Tuổi',
        'INFPRIOR2OR48HRSADMIT': 'Nhiễm Khuẩn Trước/Sau 48h Nhập Viện',
        'ISOLATEDKPNFROMINFECTIONORBLOOD': 'Phân Lập KPN Từ Máu/Nhiễm Khuẩn',
        'KPNISOUNTREATEDSTABLE': 'KPN Chưa Điều Trị Ổn Định',
        'CONSENTTOSTUDY': 'Đồng Ý Tham Gia',
        
        # Follow-up fields
        'EvaluatedAtDay28': 'Đánh Giá Ngày 28',
        'Outcome28Days': 'Kết Quả Ngày 28',
        'Rehospitalized': 'Tái Nhập Viện',
        'Dead': 'Tử Vong',
        'DeathReason': 'Nguyên Nhân Tử Vong',
        'Antb_Usage': 'Sử Dụng Kháng Sinh',
        'Func_Status': 'Tình Trạng Chức Năng',
        
        # Clinical fields
        'SEPSIS': 'Nhiễm Khuẩn Huyết',
        'SEPTICSHOCK': 'Sốc Nhiễm Khuẩn',
        'TEMPERATURE': 'Nhiệt Độ',
        'HEARTRATE': 'Nhịp Tim',
        'RESPIRATORYRATE': 'Nhịp Thở',
        'BLOODPRESSURE': 'Huyết Áp',
    }
    
    # Try to get from common labels first
    if field_name in common_labels:
        return common_labels[field_name]
    
    # ==========================================
    # MODEL-SPECIFIC LABELS
    # ==========================================
    if model_name == 'FOLLOWUPCASE':
        followup_labels = {
            'Mobility': 'Khả Năng Di Chuyển',
            'Personal_Hygiene': 'Vệ Sinh Cá Nhân',
            'Daily_Activities': 'Hoạt Động Hàng Ngày',
            'Pain_Discomfort': 'Đau/Khó Chịu',
            'Anxiety': 'Lo Âu/Trầm Cảm',
            'FBSI': 'Điểm FBSI',
        }
        if field_name in followup_labels:
            return followup_labels[field_name]
    
    elif model_name == 'LABORATORYTEST':
        lab_labels = {
            'TESTTYPE': 'Loại Xét Nghiệm',
            'TESTRESULT': 'Kết Quả',
            'TESTUNIT': 'Đơn Vị',
            'NORMALRANGE': 'Giá Trị Bình Thường',
        }
        if field_name in lab_labels:
            return lab_labels[field_name]
    
    elif model_name == 'SAMPLECOLLECTION':
        sample_labels = {
            'SPECIMENTYPE': 'Loại Mẫu',
            'COLLECTIONDATE': 'Ngày Lấy Mẫu',
            'COLLECTIONTIME': 'Giờ Lấy Mẫu',
        }
        if field_name in sample_labels:
            return sample_labels[field_name]
    
    # ==========================================
    # FALLBACK: Return field name as-is
    # ==========================================
    return field_name


# ==========================================
# EXPORT (OPTIONAL)
# ==========================================

@login_required
@require_crf_view('AuditLog', redirect_to='study_43en:audit_log_list')
def audit_log_export(request):
    """
    Export audit logs to CSV/Excel
    
    TODO: Implement export functionality
    - CSV format
    - Excel format with formatting
    - Filter by same criteria as list view
    - Include all change details
    """
    messages.info(request, 'Chức năng export đang được phát triển.')
    return redirect('study_43en:audit_log_list')
