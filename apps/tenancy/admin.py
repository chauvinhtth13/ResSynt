# models.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class StudyStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    ARCHIVED = 'archived', 'Archived'


class MembershipStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    REMOVED = 'removed', 'Removed'


class Study(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=StudyStatus.choices, default=StudyStatus.DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='created_studies')
    expected_db_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'metadata"."studies'


class StudyMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='study_memberships')
    role = models.ForeignKey("Role", on_delete=models.RESTRICT, related_name='memberships')
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_memberships')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'metadata"."study_memberships'
        unique_together = [('study', 'user')]


# admin.py
from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from .models import (
    Study,
    StudyMembership,
    MembershipStatus,
)


@admin.action(description="Activate selected memberships")
def membership_mark_active(modeladmin, request, queryset: QuerySet[StudyMembership]):
    updated = queryset.update(status=MembershipStatus.ACTIVE)
    modeladmin.message_user(request, _(f"{updated} membership(s) marked Active"), messages.SUCCESS)


@admin.action(description="Suspend selected memberships")
def membership_mark_suspended(modeladmin, request, queryset: QuerySet[StudyMembership]):
    updated = queryset.update(status=MembershipStatus.SUSPENDED)
    modeladmin.message_user(request, _(f"{updated} membership(s) marked Suspended"), messages.SUCCESS)


@admin.action(description="Mark selected memberships as Removed")
def membership_mark_removed(modeladmin, request, queryset: QuerySet[StudyMembership]):
    updated = queryset.update(status=MembershipStatus.REMOVED)
    modeladmin.message_user(request, _(f"{updated} membership(s) marked Removed"), messages.SUCCESS)


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ("code", "slug", "title", "status", "created_by", "expected_db_name", "created_at", "updated_at")
    list_filter = ("status", "created_by")
    search_fields = ("code", "slug", "title", "expected_db_name")
    readonly_fields = ("expected_db_name", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    list_select_related = ("created_by",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by").only(
            "id", "code", "slug", "title", "status", "created_by_id", "expected_db_name",
            "created_at", "updated_at", "deleted_at"
        )


@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "study", "role", "status", "added_by", "created_at", "updated_at")
    search_fields = ("user__username", "study__code", "role__name", "role__abbr")
    list_filter = ("status", "role")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50

    raw_id_fields = ("user", "added_by")
    autocomplete_fields = ("study", "role")
    list_select_related = ("user", "added_by", "study", "role")
    actions = (membership_mark_active, membership_mark_suspended, membership_mark_removed)

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("user", "added_by", "study", "role")
            .only(
                "id", "status", "created_at", "updated_at",
                "user_id", "added_by_id", "study_id", "role_id",
                "user__username", "added_by__username", "study__code",
                "role__abbr", "role__name"
            )
        )
