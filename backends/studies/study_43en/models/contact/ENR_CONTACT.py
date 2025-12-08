# backends/studies/study_43en/models/contact/Enrollment.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date
from dateutil.relativedelta import relativedelta


class ENR_CONTACT(AuditFieldsMixin):
    """
    Contact enrollment information with optimized queries and validation
    
    Similar to patient enrollment but for contacts (household members)
    
    Inherits from AuditFieldsMixin:
    - version: Optimistic locking version control
    - last_modified_by_id: User ID who last modified
    - last_modified_by_username: Username backup for audit
    - last_modified_at: Timestamp of last modification
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class SexChoices(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
    
    class ThreeStateChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        UNKNOWN = 'unknown', _('Unknown')
    
    # ==========================================
    # MANAGERS
    # ==========================================
        


    FULLNAME = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_('Full Name'),
        help_text=_('Contact full name (confidential)')
    )

    PHONE = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('Phone Number'),
        help_text=_('Contact phone number')
    )
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'SCR_CONTACT',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Contact ID'),
        related_name='enrollment_contact'
    )
    
    # ==========================================
    # ENROLLMENT INFORMATION
    # ==========================================
    ENRDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Enrollment Date'),
        help_text=_('Date contact enrolled in the study')
    )
    
    RELATIONSHIP = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,  # For relationship analysis
        verbose_name=_('Relationship to Patient'),
        help_text=_('e.g., spouse, child, parent, sibling')
    )
    
    # ==========================================
    # BIRTH INFORMATION - SIMPLIFIED VALIDATION
    # ==========================================
    DAYOFBIRTH = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name=_('Day of Birth')
    )
    
    MONTHOFBIRTH = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_('Month of Birth')
    )
    
    YEAROFBIRTH = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1900)],
        verbose_name=_('Year of Birth')
    )
    
    AGEIFDOBUNKNOWN = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        verbose_name=_('Age (if DOB unknown)'),
        help_text=_('Use this field only if date of birth is unknown')
    )
    
    # ==========================================
    # BASIC DEMOGRAPHICS
    # ==========================================
    SEX = models.CharField(
        max_length=10,
        choices=SexChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Sex')
    )
    
    ETHNICITY = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Ethnicity')
    )
    
    SPECIFYIFOTHERETHNI = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Other Ethnicity Details'),
        help_text=_('Required if ethnicity is "Other"')
    )
    
    OCCUPATION = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Occupation')
    )
    
    # ==========================================
    # RISK FACTORS / HEALTHCARE EXPOSURE
    # ==========================================
    HOSP2D6M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Hospitalized ≥2 days in last 6 months')
    )
    
    DIAL3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Dialysis in last 3 months')
    )
    
    CATHETER3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Catheter in last 3 months')
    )
    
    SONDE3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Urinary catheter in last 3 months')
    )
    
    HOME_WOUND_CARE = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Home Wound Care')
    )
    
    LONG_TERM_CARE = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Long-term Care Facility')
    )
    
    CORTICOIDPPI = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Corticoid or PPI Use')
    )
    
    # ==========================================
    # UNDERLYING CONDITIONS FLAG
    # ==========================================
    UNDERLYINGCONDS = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Has Underlying Conditions')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'ENR_CONTACT'
        verbose_name = _('Contact Enrollment')
        verbose_name_plural = _('Contact Enrollments')
        ordering = ['-ENRDATE']
        indexes = [
            models.Index(fields=['ENRDATE'], name='idx_cenr_date'),  #  Changed
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_cenr_modified'),  #  Changed
            models.Index(fields=['SEX', 'ENRDATE'], name='idx_cenr_sex_date'),  #  Changed
            models.Index(fields=['RELATIONSHIP'], name='idx_cenr_relationship'),  #  Changed
            models.Index(fields=['UNDERLYINGCONDS', 'ENRDATE'], name='idx_cenr_conds_date'),  #  Changed
        ]
    
    def __str__(self):
        return f"{self.USUBJID.USUBJID}"
    
    @cached_property
    def SITEID(self):
        """Get SITEID from related SCR_CONTACT (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def related_patient_usubjid(self):
        """Get related patient's USUBJID (cached)"""
        if self.USUBJID and self.USUBJID.SUBJIDENROLLSTUDY:
            return self.USUBJID.SUBJIDENROLLSTUDY.USUBJID
        return None
    
    @cached_property
    def calculated_age(self):
        """
        Calculate age from DOB or return provided age
        Returns: (age: float, is_calculated: bool)
        """
        if all([self.DAYOFBIRTH, self.MONTHOFBIRTH, self.YEAROFBIRTH]):
            try:
                birth_date = date(self.YEAROFBIRTH, self.MONTHOFBIRTH, self.DAYOFBIRTH)
                reference_date = self.ENRDATE or date.today()
                age = relativedelta(reference_date, birth_date)
                return (age.years + age.months/12 + age.days/365, True)
            except ValueError:
                return (self.AGEIFDOBUNKNOWN, False) if self.AGEIFDOBUNKNOWN else (None, False)
        return (self.AGEIFDOBUNKNOWN, False) if self.AGEIFDOBUNKNOWN else (None, False)
    
    @property
    def age_at_enrollment(self):
        """Get age at enrollment (for display)"""
        age, _ = self.calculated_age
        return age
    
    @property
    def has_complete_dob(self):
        """Check if full DOB is available"""
        return all([self.DAYOFBIRTH, self.MONTHOFBIRTH, self.YEAROFBIRTH])
    
    def clean(self):
        """Validation - LESS STRICT than patient"""
        errors = {}
        
        # Validate birth date if all components provided
        if all([self.DAYOFBIRTH, self.MONTHOFBIRTH, self.YEAROFBIRTH]):
            try:
                birth_date = date(self.YEAROFBIRTH, self.MONTHOFBIRTH, self.DAYOFBIRTH)
                
                # Only check if birth date is in future (basic check)
                if birth_date > date.today():
                    errors['YEAROFBIRTH'] = _('Date of birth cannot be in the future')
                        
            except ValueError:
                errors['DAYOFBIRTH'] = _('Invalid date combination')
        
        # Validate other ethnicity specification
        if self.ETHNICITY and self.ETHNICITY.lower() == 'other':
            if not self.SPECIFYIFOTHERETHNI or not self.SPECIFYIFOTHERETHNI.strip():
                errors['SPECIFYIFOTHERETHNI'] = _(
                    'Please specify ethnicity when "Other" is selected'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to clear cache and auto-set fields"""
        # Clear cached properties
        if hasattr(self, '_calculated_age'):
            del self._calculated_age
        if hasattr(self, '_SITEID'):
            del self._SITEID
        if hasattr(self, '_related_patient_usubjid'):
            del self._related_patient_usubjid
        
        # Auto-set UNDERLYINGCONDS flag if underlying condition exists
        if self.pk:
            try:
                underlying = self.underlying_condition
                self.UNDERLYINGCONDS = underlying.has_any_condition if underlying else False
            except:
                pass
        
        super().save(*args, **kwargs)