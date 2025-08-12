# apps/tenancy/middleware.py
import logging
import threading
import time
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .db_router import set_current_db

# Chuẩn: models.py nên định nghĩa Study, StudyMembership map tới metadata.studies / study_memberships
from .models import Study, StudyMembership  # <-- Đảm bảo models.py có class Study

logger = logging.getLogger(__name__)

# Lazy-load danh sách DB nghiên cứu (tránh query ở app init)
_DYNAMIC_LOADED = False
_DYNAMIC_LOCK = threading.Lock()
_DYNAMIC_LAST_LOAD = 0
_DYNAMIC_TTL = int(getattr(settings, "STUDY_DB_AUTO_REFRESH_SECONDS", "300"))  # 5 phút

def _ensure_dynamic_dbs_loaded():
    """Nạp các DB nghiên cứu active vào connections.databases (1 lần / TTL)."""
    global _DYNAMIC_LOADED, _DYNAMIC_LAST_LOAD
    now = time.time()
    if _DYNAMIC_LOADED and (now - _DYNAMIC_LAST_LOAD) < _DYNAMIC_TTL:
        return
    with _DYNAMIC_LOCK:
        if _DYNAMIC_LOADED and (now - _DYNAMIC_LAST_LOAD) < _DYNAMIC_TTL:
            return
        try:
            from .db_loader import load_active_study_databases
            load_active_study_databases()
            _DYNAMIC_LOADED = True
            _DYNAMIC_LAST_LOAD = time.time()
        except Exception as e:
            logger.error("Dynamic DB load failed: %s", e)

class StudyRoutingMiddleware(MiddlewareMixin):
    """
    - Lazy-load dynamic DB.
    - Lấy study_code từ URL kwarg <study_code> hoặc header X-Study-Code.
    - Kiểm tra membership user đối với study active.
    - Set alias DB theo study.database_name (vd: db_study_43en).
    """

    def process_request(self, request):
        # 1) Đảm bảo danh sách DB study đã được nạp
        _ensure_dynamic_dbs_loaded()

        # 2) Lấy study_code
        study_code = None
        if request.resolver_match and "study_code" in request.resolver_match.kwargs:
            study_code = request.resolver_match.kwargs["study_code"]
        elif "X-Study-Code" in request.headers:
            study_code = request.headers["X-Study-Code"]

        # Không có study_code -> dùng db_management
        if not study_code:
            set_current_db("db_management")
            return

        # 3) Tìm study active theo code (code trong DB đã chuẩn hoá lowercase)
        study = (
            Study.objects.using("db_management")
            .filter(code=study_code.lower(), status="active")
            .first()
        )
        if not study:
            logger.warning("Study '%s' không tồn tại hoặc không active.", study_code)
            return HttpResponseForbidden("Invalid or inactive study.")

        # 4) Yêu cầu user đăng nhập
        if not request.user.is_authenticated:
            logger.warning("User chưa đăng nhập nhưng truy cập study '%s'.", study_code)
            return HttpResponseForbidden("Authentication required.")

        # 5) Kiểm tra membership
        membership = (
            StudyMembership.objects.using("db_management")
            .select_related("role", "study")
            .filter(study=study, user=request.user)
            .first()
        )
        if not membership:
            logger.warning("User %s không có quyền vào study '%s'.", request.user.username, study_code)
            return HttpResponseForbidden("No access to this study.")

        # 6) Xác thực alias DB hợp lệ theo prefix
        alias = study.database_name  # <-- đúng field theo schema metadata.studies
        prefix = getattr(settings, "STUDY_DB_PREFIX", "db_study_")
        if not isinstance(alias, str) or not alias.startswith(prefix):
            logger.error("Study '%s' có database_name không hợp lệ: %r", study_code, alias)
            return HttpResponseForbidden("Study DB misconfigured.")

        # 7) Đặt DB alias cho ORM và gắn vào request
        set_current_db(alias)
        request.study = study
        request.study_role = membership.role
