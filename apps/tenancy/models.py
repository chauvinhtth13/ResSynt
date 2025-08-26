# apps/tenancy/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from parler.models import TranslatableModel, TranslatedFields

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
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when the record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when the record was last updated."),
    )

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
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when the record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when the record was last updated."),
    )

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

class Study(TranslatableModel):
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
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Database Name"),
        help_text=_("Name of the database for this study (e.g., db_study_001)."),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
        help_text=_("Current status of the study (active, inactive, archived)."),
    )
    sites = models.ManyToManyField(
        "Site",
        through="StudySite",
        related_name="studies",
        verbose_name=_("Sites"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when the record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when the record was last updated."),
    )

    translations = TranslatedFields(
        name=models.CharField(
            max_length=255,
            db_index=True,
            verbose_name=_("Name"),
            help_text=_("Name of the study."),
        ),
        introduction=models.TextField(
            blank=True,
            null=True,
            verbose_name=_("Introduction"),
            help_text=_("Brief introduction or description of the study."),
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_information'
        verbose_name = _("Study")
        verbose_name_plural = _("Study Information")
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(check=models.Q(db_name__istartswith=settings.STUDY_DB_PREFIX), name="db_name_prefix_check")
        ]
        indexes = [
            models.Index(fields=["status", "code"], name="ix_study_status_code"),
        ]

    def __str__(self):
        return str(self.safe_translation_getter("name") or self.code)

class Site(TranslatableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Site Code"),
        help_text=_("Unique global code for the site (e.g., SITE01)."),
    )
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name=_("Abbreviation"),
        help_text=_("Short abbreviation for the site (e.g., S01)."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when the record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when the record was last updated."),
    )

    translations = TranslatedFields(
        name=models.CharField(
            max_length=255,
            verbose_name=_("Name"),
            help_text=_("Name of the site."),
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_sites'
        verbose_name = _("Study Site")
        verbose_name_plural = _("Study Sites")
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                check=models.Q(abbreviation__regex=r"^[A-Z0-9]{2,10}$"),
                name="site_abbreviation_check",
            )
        ]

    def __str__(self) -> str:
        return str(self.safe_translation_getter("name") or self.code)

class StudySite(models.Model):
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="study_sites",
        verbose_name=_("Study"),
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="study_sites",
        verbose_name=_("Site"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("Timestamp when the record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Timestamp when the record was last updated."),
    )

    class Meta:
        db_table = 'study_site_links'
        verbose_name = _("Study-Site Link")
        verbose_name_plural = _("Study-Site Links")
        constraints = [
            models.UniqueConstraint(
                fields=("study", "site"),
                name="uq_study_site",
            )
        ]
        indexes = [
            models.Index(fields=["study"], name="ix_studysite_study"),
            models.Index(fields=["site"], name="ix_studysite_site"),
        ]

    def __str__(self):
        return f"{self.study.code} - {self.site.code}"

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
    study_site = models.ForeignKey(
        StudySite,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Study Site"),
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
                fields=("user", "study", "study_site", "role"),
                name="uq_user_study_site_role",
            )
        ]
        indexes = [
            models.Index(fields=["user"], name="ix_membership_user"),
            models.Index(fields=["study"], name="ix_membership_study"),
            models.Index(fields=["study_site"], name="ix_membership_site"),
            models.Index(fields=["role"], name="ix_membership_role"),
            models.Index(fields=["user", "study"], name="ix_membership_user_study"),
        ]

    def __str__(self):
        user_repr = getattr(self.user, "username", None) or getattr(self.user, "email", None) or f"User#{self.user.pk}"
        site_str = f" - {self.study_site.site.code}" if self.study_site else ""
        return f"{user_repr} - {self.study.code}{site_str} - {self.role}"

    def save(self, *args, **kwargs):
        if self.study_site and self.study_site.study != self.study:
            raise ValueError("The study_site must belong to the same study.")
        super().save(*args, **kwargs)