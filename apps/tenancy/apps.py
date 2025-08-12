# apps/tenancy/apps.py
from django.apps import AppConfig

class TenancyConfig(AppConfig):
    """
    AppConfig cho module Tenancy/Metadata.
    Lưu ý: KHÔNG truy vấn database trong ready() để tránh RuntimeWarning (Django 5+).
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenancy"
    verbose_name = "ResSync Tenancy & Metadata"

    def ready(self):
        # Chỉ import để đăng ký signal handlers; không được chạm DB ở đây.
        # File apps/tenancy/signals.py có thể lắng nghe post_migrate để refresh dynamic DB.
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Không để lỗi import làm hỏng quá trình khởi động
            pass