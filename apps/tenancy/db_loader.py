# apps/tenancy/db_loader.py
import logging
from typing import Dict
from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)


def _study_db_config(db_name: str) -> Dict:
    mgmt = settings.DATABASES.get("db_management") or settings.DATABASES.get("default")
    return {
        "ENGINE": getattr(settings, "STUDY_DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": db_name,
        "USER": getattr(settings, "STUDY_DB_USER", mgmt.get("USER")),
        "PASSWORD": getattr(settings, "STUDY_DB_PASSWORD", mgmt.get("PASSWORD")),
        "HOST": getattr(settings, "STUDY_DB_HOST", mgmt.get("HOST")),
        "PORT": getattr(settings, "STUDY_DB_PORT", mgmt.get("PORT")),
        "OPTIONS": {"options": f"-c search_path={getattr(settings, 'STUDY_DB_SEARCH_PATH', 'public')}"},
        "CONN_MAX_AGE": mgmt.get("CONN_MAX_AGE", 600),
        "ATOMIC_REQUESTS": mgmt.get("ATOMIC_REQUESTS", False),  # <-- THÊM DÒNG NÀY
        "AUTOCOMMIT": mgmt.get("AUTOCOMMIT", True),            # (tuỳ chọn, cho đủ bộ)
        "CONN_HEALTH_CHECKS": mgmt.get("CONN_HEALTH_CHECKS", False),  # (tuỳ chọn)
        "TIME_ZONE": mgmt.get("TIME_ZONE", settings.TIME_ZONE),       # (tuỳ chọn)
    }


def load_active_study_databases() -> None:
    """
    Đọc metadata.studies (status='active') từ db_management và nạp cấu hình DB
    vào connections.databases cho từng study theo tên alias = database_name.
    Chỉ thêm mới nếu alias chưa tồn tại.
    """
    # Lấy kết nối DB quản lý
    if "db_management" not in connections.databases:
        # fallback: cho phép dùng 'default' làm db_management nếu trỏ cùng DB
        logger.debug("db_loader: 'db_management' alias không thấy, dùng 'default' thay thế nếu có.")
        if "default" not in connections.databases:
            logger.error("db_loader: Không có alias 'db_management' hay 'default' trong settings.DATABASES.")
            return
        mgmt_alias = "default"
    else:
        mgmt_alias = "db_management"

    # Query danh sách study active
    try:
        with connections[mgmt_alias].cursor() as cur:
            cur.execute("""
                SELECT code, database_name
                FROM metadata.studies
                WHERE status = 'active'
            """)
            rows = cur.fetchall()
    except Exception as e:
        logger.error("db_loader: Không thể truy vấn metadata.studies từ %s: %s", mgmt_alias, e)
        return

    prefix = getattr(settings, "STUDY_DB_PREFIX", "db_study_")
    added = 0

    for code, dbname in rows:
        if not dbname or not isinstance(dbname, str):
            logger.warning("db_loader: Bỏ qua study '%s' do database_name rỗng/không hợp lệ.", code)
            continue

        if not dbname.startswith(prefix):
            logger.warning(
                "db_loader: Bỏ qua study '%s' vì database_name='%s' không bắt đầu bằng prefix '%s'.",
                code, dbname, prefix
            )
            continue

        if dbname in connections.databases:
            # Đã có alias rồi -> bỏ qua (tránh ghi đè cấu hình hiện có)
            continue

        try:
            connections.databases[dbname] = _study_db_config(dbname)
            added += 1
        except Exception as e:
            logger.error("db_loader: Lỗi khi thêm cấu hình DB cho '%s': %s", dbname, e)

    if added:
        logger.info("Dynamic DB: added %d active study database(s).", added)
    else:
        logger.info("Dynamic DB: no new active study databases to add.")
