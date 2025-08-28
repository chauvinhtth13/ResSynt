# apps/tenancy/models.py
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from parler.models import TranslatableModel, TranslatedFields

class Role(models.Model):
    title = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Title",
        validators=[RegexValidator(r'^[A-Za-z0-9\s\-]+$')],
    )
    responsibilities = models.TextField(
        verbose_name="Responsibilities",
        help_text="Description of the role's responsibilities.",
    )
    abbreviation = models.CharField(
        max_length=5,
        unique=True,
        db_index=True,
        verbose_name="Abbreviation",
        validators=[RegexValidator(r'^[A-Z]{2,5}$')],
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Timestamp when the record was last updated.",
    )

    class Meta:
        db_table = 'study_roles'
        verbose_name = "Role"
        verbose_name_plural = "Roles in Study"
        ordering = ("title",)
        constraints = [
            models.CheckConstraint(
                check=models.Q(abbreviation__regex=r"^[A-Z]{2,5}$"),
                name="roles_abbreviation_check",
            )
        ]
    
    def clean(self):
        if self.abbreviation and not self.abbreviation.isupper():
            self.abbreviation = self.abbreviation.upper()
        super().clean()

    def __str__(self):
        return self.title or f"Role#{self.pk}"

class Permission(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Code",
        help_text="Unique code for the permission (e.g., manage_db).",
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Name",
        help_text="Name of the permission (e.g., Manage Database).",
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Detailed description of the permission.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Timestamp when the record was last updated.",
    )

    class Meta:
        db_table = 'study_permissions'
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
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
        verbose_name="Role",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name="Permission",
    )

    class Meta:
        db_table = 'study_role_permissions'
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
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
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Code",
        help_text="Unique code for the study (e.g., STUDY001).",
    )
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Database Name",
        help_text="Name of the database for this study (e.g., db_study_001).",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the study (active, inactive, archived).",
    )
    sites = models.ManyToManyField(
        "Site",
        through="StudySite",
        related_name="studies",
        verbose_name="Sites",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Timestamp when the record was last updated.",
    )

    translations = TranslatedFields(
        name=models.CharField(
            max_length=255,
            db_index=True,
            verbose_name="Name",
            help_text="Name of the study.",
        ),
        introduction=models.TextField(
            blank=True,
            null=True,
            verbose_name="Introduction",
            help_text="Brief introduction or description of the study.",
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_information'
        verbose_name = "Study"
        verbose_name_plural = "Study Information"
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(check=models.Q(db_name__istartswith=settings.STUDY_DB_PREFIX), name="db_name_prefix_check")
        ]
        indexes = [
            models.Index(fields=["status", "code"], name="ix_study_status_code"),
        ]

    def clean(self):
        if not self.db_name.startswith(settings.STUDY_DB_PREFIX):
            raise ValidationError(
                f"Database name must start with {settings.STUDY_DB_PREFIX}"
            )
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        # Changed to return code instead of name
        return self.code

class Site(TranslatableModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Site Code",
        help_text="Unique global code for the site (e.g., SITE01).",
    )
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Abbreviation",
        help_text="Short abbreviation for the site (e.g., S01).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Timestamp when the record was last updated.",
    )

    translations = TranslatedFields(
        name=models.CharField(
            max_length=255,
            verbose_name="Name",
            help_text="Name of the site.",
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_sites'
        verbose_name = "Study Site"
        verbose_name_plural = "Study Sites"
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
        verbose_name="Study",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="study_sites",
        verbose_name="Site",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Timestamp when the record was last updated.",
    )

    class Meta:
        db_table = 'study_site_links'
        verbose_name = "Study-Site Link"
        verbose_name_plural = "Study-Site Links"
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
        verbose_name="User",
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Study",
    )
    study_site = models.ForeignKey(
        StudySite,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Study Site",
        null=True,
        blank=True,
        help_text="Optional site within the study; null for study-level access.",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.RESTRICT,
        related_name="study_memberships",
        verbose_name="Role",
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Assigned At")

    class Meta:
        db_table = 'study_membership'
        verbose_name = "Study Membership"
        verbose_name_plural = "Study Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "study", "study_site", "role"),
                name="uq_user_study_site_role",
                condition=models.Q(study_site__isnull=False)
            ),
            models.UniqueConstraint(
                fields=("user", "study", "role"),
                name="uq_user_study_role",
                condition=models.Q(study_site__isnull=True)
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

    def clean(self):
        if self.study_site and self.study_site.study_id != self.study_id: # type: ignore
            raise ValidationError("Study site must belong to the selected study")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)