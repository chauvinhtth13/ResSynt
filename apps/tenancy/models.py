# apps/tenancy/models.py

from django.db import models
from django.conf import settings

class Study(models.Model):
    """
    Lưu thông tin từng nghiên cứu và thông số kết nối đến database nghiên cứu vật lý.
    """
    study_code = models.CharField(max_length=64, unique=True)  # Ví dụ: 'study_43en'
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, default='active')
    db_name = models.CharField(max_length=128, unique=True)    # Tên DB vật lý
    db_user = models.CharField(max_length=64)
    db_password = models.CharField(max_length=128)
    db_host = models.CharField(max_length=128, default='localhost')
    db_port = models.IntegerField(default=5432)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True, related_name='created_studies'
    )

    def __str__(self):
        return f"{self.study_code} - {self.name}"


class StudyMembership(models.Model):
    """
    Mapping user <-> nghiên cứu + role
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=32,
        choices=[
            ('admin', 'Admin'),
            ('editor', 'Editor'),
            ('viewer', 'Viewer'),
        ],
        default='viewer'
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'study')
        verbose_name = 'Study Membership'
        verbose_name_plural = 'Study Memberships'

    def __str__(self):
        return f"{self.user.username} @ {self.study.study_code} ({self.role})"


class AuditLog(models.Model):
    """
    Log audit các hành động quan trọng (có thể mở rộng thêm tuỳ ý)
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    study = models.ForeignKey(Study, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.created_at} - {self.user}: {self.action}"

class SystemSetting(models.Model):
    """
    Lưu cấu hình hệ thống chung nếu cần
    """
    key = models.CharField(max_length=64, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.key}"
