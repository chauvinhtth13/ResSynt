# backend/tenancy/models/study.py - FIXED VERSION
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


class Study(TranslatableModel):
    """Study/Research Project - Main tenant entity"""
    
    class Status(models.TextChoices):
        PLANNING = 'planning', _('Planning')
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Study Code"),
        help_text=_("Unique code for the study (e.g., STUDY001)"),
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message=_("Code must contain only uppercase letters, numbers, and underscores")
        )]
    )
    
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Database Name"),
        help_text=_("Name of the database for this study")
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
        verbose_name=_("Status")
    )
    
    # Relationships
    sites = models.ManyToManyField(
        "Site",
        through="StudySite",
        related_name="studies",
        verbose_name=_("Sites")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='studies_created',
        verbose_name=_("Created By")
    )

    # Translatable fields
    translations = TranslatedFields(
        name=models.CharField(
            max_length=255,
            db_index=True,
            verbose_name=_("Name")
        )
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_information'  # FIXED: Added management schema
        verbose_name = _("Studies Information")
        verbose_name_plural = _("Studies Information")
        ordering = ['-created_at', 'code']
        indexes = [
            models.Index(fields=['status', 'code'], name='idx_study_status_code'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(db_name__regex=r'^db_study_\w+$'),
                name='study_db_name_format'
            )
        ]

    def clean(self):
        if self.db_name and not self.db_name.startswith('db_study_'):
            self.db_name = f'db_study_{self.code.lower()}'
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.safe_translation_getter('name', any_language=True)
        return f"{self.code} - {name}" if name else self.code


class Site(TranslatableModel):
    """Research Site/Location"""
    
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Site Code"),
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message=_("Code must contain only uppercase letters, numbers, and underscores")
        )]
    )
    
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name=_("Abbreviation")
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    # Translatable fields
    translations = TranslatedFields(
        name=models.CharField(
            max_length=255,
            verbose_name=_("Name")
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_sites'  # FIXED: Added management schema
        verbose_name = _("Study Sites")
        verbose_name_plural = _("Study Sites")
        ordering = ['code']
        indexes = [
            models.Index(fields=['code'], name='idx_site_code'),
        ]

    def __str__(self):
        name = self.safe_translation_getter('name', any_language=True)
        return f"{self.code} - {name}" if name else self.code


class StudySite(models.Model):
    """Link between Study and Site with specific configuration"""
    
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="study_sites",
        verbose_name=_("Study")
    )
    
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="site_studies",
        verbose_name=_("Site")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        db_table = 'study_site_links'  # FIXED: Added management schema
        verbose_name = _("Study-Site Links")
        verbose_name_plural = _("Study-Site Links")
        constraints = [
            models.UniqueConstraint(
                fields=['study', 'site'],
                name='unique_study_site'
            )
        ]
        indexes = [
            models.Index(fields=['study'], name='idx_studysite'),
            models.Index(fields=["site"], name="ix_studysite_site"),
        ]

    def __str__(self):
        return f"{self.study.code} - {self.site.code}"