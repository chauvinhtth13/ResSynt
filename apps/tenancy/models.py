# apps/tenancy/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models.query import QuerySet  # For type hint
from typing import cast  # For type casting to satisfy Pylance

class Role(models.Model):
    title = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Title"),
        help_text=_("Unique title for the role (e.g., Database Administrator)."),
    )
    responsibilities = models.TextField(
        verbose_name=_("Responsibilities"),
        help_text=_("Description of the role's responsibilities."),
    )
    abbreviation = models.CharField(
        max_length=5,
        unique=True,
        db_index=True,
        verbose_name=_("Abbreviation"),
        help_text=_("Short code for the role (2-5 uppercase letters, e.g., DBA)."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = 'study_roles'
        verbose_name = _("Role")
        verbose_name_plural = _("Roles in Study")
        ordering = ("title",)
        constraints = [
            models.CheckConstraint(
                check=models.Q(abbreviation__regex=r"^[A-Z]{2,5}$"),
                name="roles_abbreviation_check",
            )
        ]

    def __str__(self):
        return self.title or f"Role#{self.pk}"

class Permission(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Unique code for the permission (e.g., manage_db)."),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("Human-readable name of the permission (e.g., Manage Database)."),
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed description of the permission."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = 'study_permissions'
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ("code",)
        indexes = [
            models.Index(fields=["name"], name="ix_perm_name"),
        ]

    def __str__(self):
        return self.name or self.code

class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name=_("Role"),
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name=_("Permission"),
    )

    class Meta:
        db_table = 'study_role_permissions'
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        constraints = [
            models.UniqueConstraint(
                fields=("role", "permission"),
                name="uq_role_permission",
            )
        ]
        indexes = [
            models.Index(fields=["role"], name="ix_roleperm_role"),
            models.Index(fields=["permission"], name="ix_roleperm_perm"),
        ]

    def __str__(self):
        return f"{self.role} - {self.permission}"

class Study(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        ARCHIVED = "archived", _("Archived")

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Unique code for the study (e.g., STUDY001)."),
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_("Name"),
        help_text=_("Name of the study."),
    )
    introduction = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Introduction"),
        help_text=_("Brief introduction or description of the study."),
    )
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Database Name"),
        help_text=_("Name of the database for this study (e.g., db_study_001)."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Current status of the study (active, inactive, archived)."),
    )
    translations = models.Manager()
    class Meta:
        db_table = 'study_information'
        verbose_name = _("Study")
        verbose_name_plural = _("Study Information")
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                check=models.Q(db_name__regex=r"^[A-Za-z0-9_]+$"),
                name="valid_db_name",
            )
        ]
        indexes = [
            models.Index(fields=["status", "code"], name="ix_study_status_code"),
        ]

    def __str__(self):
        return self.code

    def get_translated_name(self, language_code=None):
        """
        Return translated name by language_code; fallback to default name.
        """
        lang = (language_code or getattr(settings, "LANGUAGE_CODE", None)) or "en"
        translations_qs = cast(QuerySet[StudyTranslation], self.translations)
        return translations_qs.filter(language_code=lang).values_list("name", flat=True).first() or self.name

class StudyTranslation(models.Model):
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Study"),
    )
    language_code = models.CharField(
        max_length=16,
        db_index=True,
        verbose_name=_("Language Code"),
        help_text=_("Language code for the translation (e.g., vi, en, en-US)."),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Translated Name"),
        help_text=_("Translated name of the study."),
    )
    introduction = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Translated Introduction"),
        help_text=_("Translated introduction of the study."),
    )

    class Meta:
        db_table = 'study_translations'
        verbose_name = _("Study Translation")
        verbose_name_plural = _("Study Translations")
        ordering = ("study_id", "language_code")
        constraints = [
            models.UniqueConstraint(
                fields=("study", "language_code"),
                name="uq_study_lang",
            ),
            models.CheckConstraint(
                check=models.Q(language_code__regex=r"^[A-Za-z]{2,3}([-_][A-Za-z0-9]+)*$"),
                name="valid_language_code",
            ),
        ]
        indexes = [
            models.Index(fields=["study", "language_code"], name="ix_study_lang"),
        ]

    def __str__(self):
        return f"{self.study.code} ({self.language_code})"

class StudySite(models.Model):
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="sites",
        verbose_name=_("Study"),
    )
    code = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Site Code"),
        help_text=_("Unique code for the site within the study (e.g., SITE01)."),
    )
    name_en = models.CharField(
        max_length=255,
        verbose_name=_("Name (English)"),
        help_text=_("English name of the site."),
    )
    name_vi = models.CharField(
        max_length=255,
        verbose_name=_("Name (Vietnamese)"),
        help_text=_("Vietnamese name of the site."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = 'study_sites'
        verbose_name = _("Study Site")
        verbose_name_plural = _("Study Sites")
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                fields=("study", "code"),
                name="uq_study_site_code",
            )
        ]
        indexes = [
            models.Index(fields=["study", "code"], name="ix_site_study_code"),
        ]

    def __str__(self):
        return f"{self.study.code} - {self.code}"

class StudyMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_memberships",
        verbose_name=_("User"),
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Study"),
    )
    site = models.ForeignKey(
        StudySite,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Site"),
        null=True,
        blank=True,
        help_text=_("Optional site within the study; null for study-level access."),
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.RESTRICT,
        related_name="study_memberships",
        verbose_name=_("Role"),
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Assigned At"))

    class Meta:
        db_table = 'study_membership'
        verbose_name = _("Study Membership")
        verbose_name_plural = _("Study Memberships")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "study", "site", "role"),
                name="uq_user_study_site_role",
            )
        ]
        indexes = [
            models.Index(fields=["user"], name="ix_membership_user"),
            models.Index(fields=["study"], name="ix_membership_study"),
            models.Index(fields=["site"], name="ix_membership_site"),
            models.Index(fields=["role"], name="ix_membership_role"),
            models.Index(fields=["user", "study"], name="ix_membership_user_study"),
        ]

    def __str__(self):
        user_repr = getattr(self.user, "username", None) or getattr(self.user, "email", None) or f"User#{self.user.pk}"
        site_str = f" - {self.site.code}" if self.site else ""
        return f"{user_repr} - {self.study.code}{site_str} - {self.role}"