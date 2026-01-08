from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class FU_CONTACT_28(AuditFieldsMixin):
    """
    Contact follow-up at Day 28
    Healthcare exposure and medication tracking
    
    Optimizations:
    - Added AuditFieldsMixin for compliance
    - Enhanced validation for dates
    - Cached properties for computed values
    - Better indexes for queries
    - Query helper methods
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class AssessedChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CONTACT',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='followup_28',
        verbose_name=_('Contact ID')
    )
    
    # ==========================================
    # ASSESSMENT INFORMATION
    # ==========================================
    ASSESSED = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Assessed at Day 28?')
    )
    
    ASSESSDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Assessment Date')
    )
    
    # ==========================================
    # HEALTHCARE EXPOSURE SINCE LAST VISIT
    # ==========================================
    HOSP2D = models.BooleanField(
        default=False,
        verbose_name=_('Hospitalized ≥2 days')
    )
    
    DIAL = models.BooleanField(
        default=False,
        verbose_name=_('Dialysis')
    )
    
    CATHETER = models.BooleanField(
        default=False,
        verbose_name=_('IV Catheter')
    )
    
    SONDE = models.BooleanField(
        default=False,
        verbose_name=_('Urinary Catheter')
    )
    
    HOME_WOUND_CARE = models.BooleanField(
        default=False,
        verbose_name=_('Home Wound Care')
    )
    
    LONG_TERM_CARE = models.BooleanField(
        default=False,
        verbose_name=_('Long-term Care Facility')
    )
    
    # ==========================================
    # MEDICATION USE
    # ==========================================
    MEDICATION_USE = models.BooleanField(
        default=False,
        verbose_name=_('Medication Use (corticoid, PPI, antibiotics)')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'FU_CONTACT_28'
        verbose_name = _('Contact Follow-up Day 28')
        verbose_name_plural = _('Contact Follow-ups Day 28')
        ordering = ['-ASSESSDATE']
        indexes = [
            models.Index(fields=['ASSESSDATE'], name='idx_cfu28_assess'),
            models.Index(fields=['ASSESSED', 'ASSESSDATE'], name='idx_cfu28_asses_date'),
            models.Index(fields=['MEDICATION_USE'], name='idx_cfu28_med'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_cfu28_modified'),
        ]
        constraints = [
            # If assessed YES, must have assessment date
            models.CheckConstraint(
                condition=(
                    ~models.Q(ASSESSED='Yes') |
                    models.Q(ASSESSDATE__isnull=False)
                ),
                name='cfu28_assess_date_required'
            ),
        ]
    
    def __str__(self):
        return f"Contact FU Day 28: {self.USUBJID_id}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CONTACT (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def has_healthcare_exposure(self):
        """Check if contact had any healthcare exposure"""
        return any([
            self.HOSP2D,
            self.DIAL,
            self.CATHETER,
            self.SONDE,
            self.HOME_WOUND_CARE,
            self.LONG_TERM_CARE
        ])
    
    @cached_property
    def healthcare_exposure_count(self):
        """Count number of healthcare exposures"""
        return sum([
            self.HOSP2D,
            self.DIAL,
            self.CATHETER,
            self.SONDE,
            self.HOME_WOUND_CARE,
            self.LONG_TERM_CARE
        ])
    
    @cached_property
    def healthcare_exposure_list(self):
        """Get list of healthcare exposures"""
        exposures = []
        if self.HOSP2D:
            exposures.append(_('Hospitalized ≥2 days'))
        if self.DIAL:
            exposures.append(_('Dialysis'))
        if self.CATHETER:
            exposures.append(_('IV Catheter'))
        if self.SONDE:
            exposures.append(_('Urinary Catheter'))
        if self.HOME_WOUND_CARE:
            exposures.append(_('Home Wound Care'))
        if self.LONG_TERM_CARE:
            exposures.append(_('Long-term Care Facility'))
        return exposures
    
    @property
    def days_since_enrollment(self):
        """Calculate days from enrollment to assessment"""
        if self.ASSESSDATE and self.USUBJID and self.USUBJID.ENRDATE:
            delta = self.ASSESSDATE - self.USUBJID.ENRDATE
            return delta.days
        return None
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # If assessed, must have assessment date
        if self.ASSESSED == self.AssessedChoices.YES:
            if not self.ASSESSDATE:
                errors['ASSESSDATE'] = _('Assessment date is required when contact is assessed')
        
        # Validate assessment date
        if self.ASSESSDATE:
            #  SIMPLIFIED: Only basic logical validation
            # Allow flexible scheduling - removed strict day range requirements
            try:
                if self.USUBJID and hasattr(self.USUBJID, 'ENRDATE') and self.USUBJID.ENRDATE:
                    # Only check that assessment is after enrollment (basic logic)
                    if self.ASSESSDATE < self.USUBJID.ENRDATE:
                        errors['ASSESSDATE'] = _('Assessment date cannot be before enrollment date')
            except Exception:
                # Skip validation during create when USUBJID not yet assigned
                pass
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with cache management"""
        # Clear cached properties
        self._clear_cache()
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_has_healthcare_exposure', '_healthcare_exposure_count',
            '_healthcare_exposure_list'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_assessed_cases(cls):
        """Get all cases that were assessed"""
        return cls.objects.filter(
            ASSESSED=cls.AssessedChoices.YES
        ).select_related('USUBJID')
    
    @classmethod
    def get_with_healthcare_exposure(cls):
        """Get all cases with any healthcare exposure"""
        from django.db.models import Q
        return cls.objects.filter(
            Q(HOSP2D=True) | Q(DIAL=True) | Q(CATHETER=True) |
            Q(SONDE=True) | Q(HOME_WOUND_CARE=True) | Q(LONG_TERM_CARE=True)
        ).select_related('USUBJID')
    
    @classmethod
    def get_with_medication_use(cls):
        """Get all cases with medication use"""
        return cls.objects.filter(
            MEDICATION_USE=True
        ).select_related('USUBJID')
    
    @classmethod
    def get_hospitalized_cases(cls):
        """Get all cases hospitalized ≥2 days"""
        return cls.objects.filter(
            HOSP2D=True
        ).select_related('USUBJID')