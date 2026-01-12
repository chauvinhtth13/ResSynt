# backends/audit_logs/utils/__init__.py
"""
BASE Audit Log Utils - Shared across all studies

This module provides:
- Security sanitization (XSS, SQL injection prevention)
- Change detection for audit logging
- HMAC integrity verification
- Rate limiting decorators
- Site filtering utilities

Database Schema:
    Audit tables in 'logging' schema:
    - logging.audit_log: Main entries
    - logging.audit_log_detail: Field-level changes

Export all utility classes and functions
"""
from .helpers import get_client_ip, normalize_value, format_value_for_display
from .integrity import IntegrityChecker
from .detector import ChangeDetector
from .sanitizer import SecuritySanitizer
from .validator import ReasonValidator
from .decorators import audit_log
from .rate_limiter import rate_limit

__all__ = [
    # Helpers
    'get_client_ip',
    'normalize_value',
    'format_value_for_display',
    
    # Core classes
    'IntegrityChecker',
    'ChangeDetector',
    'SecuritySanitizer',
    'ReasonValidator',
    
    # Decorators
    'audit_log',
    'rate_limit',
    
    # Legacy - deprecated (for backwards compatibility)
    'get_site_filtered_object_or_404',
    'get_queryset_for_model',
]

# ==========================================
# LEGACY FUNCTIONS (DEPRECATED - kept for backwards compatibility)
# ==========================================
from django.shortcuts import get_object_or_404
from django.http import Http404

def get_site_filtered_object_or_404(model_class, site_id=None, **kwargs):
    """
    Lấy một object từ database, có xử lý cho site_id.
    Nếu site_id là 'all' hoặc None, sẽ truy vấn từ tất cả các site.
    Nếu site_id có giá trị, sẽ kiểm tra xem object có thuộc về site đó không.
    
    Returns:
        model_class instance: Nếu tìm thấy object
        
    Raises:
        Http404: Nếu không tìm thấy object hoặc object không thuộc về site_id được chỉ định
    """
    if site_id is None or site_id == 'all':
        # Nếu không có site_id hoặc site_id là 'all', lấy object từ tất cả sites
        return get_object_or_404(model_class, **kwargs)
    else:
        # Nếu có site_id, kiểm tra đối tượng thuộc về site đó
        obj = get_object_or_404(model_class, **kwargs)
        
        # Kiểm tra xem object có thuộc về site_id không
        if hasattr(obj, 'SITEID'):
            # Nếu object có SITEID trực tiếp
            if obj.SITEID != site_id:
                raise Http404("Object không thuộc về site được chọn")
        elif hasattr(obj, 'USUBJID'):
            # Nếu object có USUBJID dạng chuỗi với prefix là site_id
            if isinstance(obj.USUBJID, str):
                if not obj.USUBJID.startswith(f"{site_id}-"):
                    raise Http404("Object không thuộc về site được chọn")
            # Nếu object có USUBJID là foreign key đến model khác
            elif hasattr(obj.USUBJID, 'USUBJID'):
                if isinstance(obj.USUBJID.USUBJID, str):
                    if not obj.USUBJID.USUBJID.startswith(f"{site_id}-"):
                        raise Http404("Object không thuộc về site được chọn")
        
        return obj

def get_queryset_for_model(model_class, site_id=None):
    """
    Trả về queryset phù hợp với model và site_id.
    Nếu site_id là 'all' hoặc None, trả về tất cả dữ liệu.
    Nếu site_id có giá trị, lọc theo site_id.
    
    Returns:
        QuerySet: Queryset đã được lọc theo site_id (nếu có)
    """
    if hasattr(model_class, 'site_objects'):
        if site_id is None or site_id == 'all':
            return model_class.objects.all()
        else:
            return model_class.site_objects.filter_by_site(site_id)
    else:
        return model_class.objects.all()
