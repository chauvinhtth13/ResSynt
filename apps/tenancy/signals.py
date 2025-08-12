# apps/tenancy/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from apps.tenancy.db_loader import load_active_study_databases

@receiver(post_migrate)
def refresh_study_dbs_after_migrate(sender, **kwargs):
    # Signal này chạy SAU migrate -> an toàn để chạm DB, không phải lúc init
    try:
        load_active_study_databases()
    except Exception:
        # tránh crash migrate nếu lỗi kết nối study DB
        pass