# apps/tenancy/models.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional
from django.conf import settings
from django.db import models
from django.utils import timezone


class Study(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"
        PROCESS = "processing", "Processing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255, blank=True, null=True)
    database_name = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'metadata"."studies'
        verbose_name = "Study"
        verbose_name_plural = "Studies"
        indexes = [
            models.Index(fields=["status"], name="idx_studies_status_model"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name or ''}"


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    priority = models.PositiveSmallIntegerField(default=100)

    class Meta:
        managed = False
        db_table = 'metadata"."roles'
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self) -> str:
        return self.label


class StudyMembership(models.Model):
    id = models.AutoField(primary_key=True)

    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        db_column="study_id",
        related_name="memberships",
        to_field="id",  # UUID
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="study_memberships",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        db_column="role_id",
        related_name="memberships",
        to_field="id",  # UUID
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        managed = False
        db_table = 'metadata"."study_memberships'
        verbose_name = "Study Membership"
        verbose_name_plural = "Study Memberships"
        unique_together = ("study", "user")
        indexes = [
            models.Index(fields=["user"], name="idx_mem_user"),
            models.Index(fields=["study"], name="idx_mem_study"),
            models.Index(fields=["study", "role"], name="idx_mem_study_role"),
        ]


    def __str__(self) -> str:
        # Tránh dùng *_id để Pylance khỏi báo; cũng thân thiện khi đọc log/admin
        return f"{self.user} → {self.study} ({self.role})"
