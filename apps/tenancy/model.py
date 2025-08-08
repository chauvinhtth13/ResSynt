from django.db import models
from django.conf import settings

class StudiesInfo(models.Model):
    id = models.UUIDField(primary_key=True)  # gen_random_uuid() do DB tạo
    study_code = models.TextField(unique=True)
    study_name = models.TextField(blank=True, null=True)
    db_name = models.TextField(unique=True)
    status = models.TextField()  # DB là ENUM nhưng Django map text
    created_at = models.DateTimeField()
    start_date = models.DateField(blank=True, null=True)  # đổi DateTimeField nếu DB là TIMESTAMPTZ
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False  # Không để Django migrate bảng này
        db_table = 'studies_management"."studies_info'  # Chỉ rõ schema và bảng

    def __str__(self):
        return f"{self.study_code} - {self.study_name or ''}"

class StudyMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="study_memberships",
    )
    study = models.ForeignKey(
        StudiesInfo,
        on_delete=models.CASCADE,
        db_column="study_id",
        related_name="memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False  # Không để Django migrate bảng này
        db_table = 'studies_management"."studies_membership'
        unique_together = ("user", "study")