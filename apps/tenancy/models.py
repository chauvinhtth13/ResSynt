# apps/tenancy/models.py
# This defines the models for the metadata schema in the main database (db_management).
# Assumptions:
# - Schema 'metadata' for these models; set via Meta db_table with schema prefix.
# - Uses Django's built-in User model from 'auth' schema for foreign keys.
# - Study model manages research info: code, name, intro, db_name, timestamps, status.
# - Role model: Per-study roles (e.g., Admin, Viewer).
# - UserStudyPermission: Links users to studies with roles, managing access rights.
# - Additional fields can be added as needed (e.g., permissions as ManyToMany if roles insufficient).
# - For PostgreSQL schema enforcement, ensure migrations create tables in 'metadata' schema.
# - To apply schema: In migrations, use operations like RunSQL("SET search_path TO metadata;") or custom migration.

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Study(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Study Code"),
        help_text=_("Unique code for the study (e.g., STUDY001)")
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Study Name"),
        help_text=_("Full name of the research study")
    )
    introduction = models.TextField(
        blank=True,
        verbose_name=_("Introduction"),
        help_text=_("Brief introduction or description of the study")
    )
    db_name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Database Name"),
        help_text=_("Name of the dedicated database for this study")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', _("Active")),
            ('inactive', _("Inactive")),
            ('archived', _("Archived"))
        ],
        default='active',
        verbose_name=_("Status"),
        help_text=_("Current status of the study")
    )

    class Meta:
        db_table = 'metadata."study"'
        verbose_name = _("Study")
        verbose_name_plural = _("Studies")
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

class Role(models.Model):
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name=_("Study")
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_("Role Name"),
        help_text=_("Name of the role (e.g., Admin, Researcher)")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description of the role's responsibilities")
    )

    class Meta:
        db_table = 'metadata."role"'
        unique_together = ['study', 'name']
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} in {self.study.code}"

class UserStudyPermission(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        help_text=_("User from Django auth schema")
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        verbose_name=_("Study")
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Role"),
        help_text=_("Assigned role in the study (optional if custom perms used)")
    )
    # Optional: Add custom permissions if needed, e.g.,
    # can_read = models.BooleanField(default=True)
    # can_write = models.BooleanField(default=False)
    # Or use Django's Permission model: permissions = models.ManyToManyField('auth.Permission')

    class Meta:
        db_table = 'metadata."user_study_permission"'
        unique_together = ['user', 'study']
        verbose_name = _("User Study Permission")
        verbose_name_plural = _("User Study Permissions")
        ordering = ['user', 'study']

    def __str__(self):
        return f"{self.user.username} - {self.role.name if self.role else 'Custom'} in {self.study.code}"

# Usage notes:
# - To create tables: Run `python manage.py makemigrations tenancy` then `python manage.py migrate tenancy`
# - Ensure PostgreSQL user has CREATE privileges on 'metadata' schema.
# - In settings.py, the search_path includes 'metadata' for queries.
# - Access control: In middleware/views, check UserStudyPermission to grant/deny access to study DB.