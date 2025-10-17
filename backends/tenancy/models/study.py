# backend/tenancy/models/study.py - COMPLETE
"""
Study and Site models
"""
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from parler.models import TranslatableModel, TranslatedFields
import logging

logger = logging.getLogger(__name__)

class Study(TranslatableModel):
    """
    Study/Research Project - Main tenant entity
    Each study has its own database
    """
    
    class Status(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Study Code",
        help_text="Unique code for the study (e.g., 43EN, 44EN) - uppercase letters, numbers, underscores only",
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message="Code must contain only uppercase letters, numbers, and underscores"
        )]
    )
    
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Database Name",
        help_text="Auto-generated from study code (e.g., db_study_43en). Leave blank for auto-generation.",
        blank=True,
        validators=[RegexValidator(
            regex=r'^db_study_[a-z0-9_]+$',
            message="Database name must start with 'db_study_' and contain only lowercase letters, numbers, and underscores"
        )]
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
        verbose_name="Status",
        help_text="Study status. Archived studies won't be loaded by the system."
    )
    
    # Relationships
    sites = models.ManyToManyField(
        "Site",
        through="StudySite",
        related_name="studies",
        verbose_name="Sites"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='studies_created',
        verbose_name="Created By"
    )

    # Translatable fields
    translations = TranslatedFields(
        name=models.TextField(
            max_length=255,
            db_index=True,
            verbose_name="Study Name"
        )
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_information'
        verbose_name = "Study Information"
        verbose_name_plural = "Study Information"
        ordering = ['-created_at', 'code']
        indexes = [
            models.Index(fields=['status', 'code'], name='idx_study_status_code'),
        ]

    def clean(self):
        """Validate and auto-generate db_name from code"""
        super().clean()
        
        if not self.code:
            raise ValidationError({'code': 'Study code is required.'})
        
        if not self.db_name:
            self.db_name = self.generate_db_name()
        
        expected_db_name = self.generate_db_name()
        if self.db_name != expected_db_name:
            raise ValidationError({
                'db_name': f"Database name must be '{expected_db_name}' for study code '{self.code}'. "
                           f"Leave blank for auto-generation."
            })

    def save(self, *args, **kwargs):
        """Override save to auto-generate db_name"""
        if not self.db_name:
            self.db_name = self.generate_db_name()
        
        self.full_clean()
        
        super().save(*args, **kwargs)

    def generate_db_name(self) -> str:
        """Generate database name from study code"""
        if not self.code:
            raise ValidationError("Study code is required")
        
        # Use settings.STUDY_DB_PREFIX (correct)
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        return f"{prefix}{self.code.lower()}"

    def __str__(self):
        name = self.safe_translation_getter('name', any_language=True)
        return f"{self.code} - {name}" if name else self.code


class Site(TranslatableModel):
    """Research Site/Location"""
    
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Site Code",
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message="Code must contain only uppercase letters, numbers, and underscores"
        )]
    )
    
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Abbreviation"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    translations = TranslatedFields(
        name=models.TextField(
            max_length=255,
            verbose_name="Name"
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_sites'
        verbose_name = "Study Sites"
        verbose_name_plural = "Study Sites"
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
        verbose_name="Study"
    )
    
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="site_studies",
        verbose_name="Site"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        db_table = 'study_site_links'
        verbose_name = "Study-Site Link"
        verbose_name_plural = "Study-Site Links"
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
    
