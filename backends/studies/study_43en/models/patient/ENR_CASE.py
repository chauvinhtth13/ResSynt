# backends/studies/study_43en/models/patient/enr_case_updated.py
"""
UPDATED ENR_CASE Model - After PII Migration

Changes:
- Removed: FULLNAME, PHONE, MEDRECORDID
- Removed: All address fields (STREET_NEW, WARD_NEW, etc.)
- Removed: PRIMARY_ADDRESS
- Added: property access to personal_data relationship
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from backends.studies.study_43en.models.patient.PERSONAL_DATA import PERSONAL_DATA
from datetime import date
from dateutil.relativedelta import relativedelta


class ENR_CASE(AuditFieldsMixin):
    """
    Patient enrollment information (NON-PII fields only)
    
    PII fields moved to PERSONAL_DATA model for better security
    Access via: enrollment_case.personal_data.FULLNAME, etc.
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class SexChoices(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
        OTHER = 'Other', _('Other')
    
    class ResidenceTypeChoices(models.TextChoices):
        URBAN = 'urban', _('Urban')
        SUBURBAN = 'suburban', _('Suburban')
        RURAL = 'rural', _('Rural')
    
    class WorkplaceTypeChoices(models.TextChoices):
        INDOOR = 'indoor', _('Indoor')
        OUTDOOR = 'outdoor', _('Outdoor')
    
    class ThreeStateChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        UNKNOWN = 'unknown', _('Unknown')
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'SCR_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient ID'),
        related_name='enrollment_case'
    )
    
    # ==========================================
    # ENROLLMENT INFORMATION
    # ==========================================
    ENRDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Enrollment Date'),
        help_text=_('Enrollment Date')
    )
    
    RECRUITDEPT = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Recruitment Department')
    )
    
    # ==========================================
    # BIRTH INFORMATION
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
        help_text=_('Age (if date of birth is unknown')
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
    
    OCCUPATION = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Occupation')
    )
    
    # ==========================================
    # HOSPITAL ADMISSION INFORMATION
    # ==========================================
    FROMOTHERHOSPITAL = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Transferred from another healthcare facility (HCF)?')
    )
    
    PRIORHOSPIADMISDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Admission Date at previous HCF')
    )
    
    HEALFACILITYNAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Name of HCF')
    )
    
    REASONFORADM = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for admission at previous HCF')
    )
    
    # ==========================================
    # SANITATION INFORMATION
    # ==========================================
    TOILETNUM = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Number of restrooms')
    )
    
    SHAREDTOILET = models.BooleanField(
        default=False,
        verbose_name=_('Shared restroom use')
    )
    
    # ==========================================
    # RESIDENCE AND WORKPLACE
    # ==========================================
    RESIDENCETYPE = models.CharField(
        max_length=20,
        choices=ResidenceTypeChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Residential area type')
    )
    
    WORKPLACETYPE = models.CharField(
        max_length=20,
        choices=WorkplaceTypeChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Workplace environment type')
    )
    
    # ==========================================
    # RISK FACTORS
    # ==========================================
    HOSP2D6M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Hospitalized ≥ 2 days in the 6 months before admission')
    )
    
    DIAL3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Received regular dialysis in the 3 months before admission')
    )
    
    CATHETER3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Had a central venous catheter placed in the 3 months before admission')
    )
    
    SONDE3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Had an indwelling urinary catheter placed in the 3 months before admission?')
    )
    
    HOME_WOUND_CARE = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Received home wound care?')
    )
    
    LONG_TERM_CARE = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Residing in a long-term care facility?')
    )
    
    CORTICOIDPPI = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('History of medication use (corticoid, PPI, …)')
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
        db_table = 'ENR_CASE'
        verbose_name = _('Patient Enrollment')
        verbose_name_plural = _('Patient Enrollments')
        ordering = ['-ENRDATE']
        indexes = [
            models.Index(fields=['ENRDATE'], name='idx_enr_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_enr_modified'),
            models.Index(fields=['SEX', 'ENRDATE'], name='idx_enr_sex_date'),
            models.Index(fields=['UNDERLYINGCONDS', 'ENRDATE'], name='idx_enr_conds_date'),
        ]
    
    def __str__(self):
        return f"{self.USUBJID.USUBJID}"
    
    # ==========================================
    # ✨ NEW: PII ACCESS PROPERTIES
    # ==========================================
    
    @property
    def FULLNAME(self):
        """Access full name from personal_data (backward compatibility)"""
        try:
            return self.personal_data.FULLNAME
        except:
            return None
    
    @property
    def PHONE(self):
        """Access phone from personal_data (backward compatibility)"""
        try:
            return self.personal_data.PHONE
        except:
            return None
    
    @property
    def MEDRECORDID(self):
        """Access medical record ID from personal_data (backward compatibility)"""
        try:
            return self.personal_data.MEDRECORDID
        except:
            return None
    
    @property
    def geographic_location(self):
        """Get formatted geographic location from personal_data"""
        try:
            return self.personal_data.geographic_location
        except:
            return None
    
    @property
    def full_address_new(self):
        """Get new full address from personal_data"""
        try:
            return self.personal_data.full_address_new
        except:
            return None
    
    @property
    def full_address_old(self):
        """Get old full address from personal_data"""
        try:
            return self.personal_data.full_address_old
        except:
            return None
    
    # ==========================================
    # EXISTING PROPERTIES
    # ==========================================
    
    @cached_property
    def SITEID(self):
        """Get SITEID from related SCR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def calculated_age(self):
        """Calculate age from DOB or return provided age"""
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
        """Enhanced validation"""
        errors = {}
        
        # Validate birth date if all components provided
        if all([self.DAYOFBIRTH, self.MONTHOFBIRTH, self.YEAROFBIRTH]):
            try:
                birth_date = date(self.YEAROFBIRTH, self.MONTHOFBIRTH, self.DAYOFBIRTH)
                
                if birth_date > date.today():
                    errors['YEAROFBIRTH'] = _('Date of birth cannot be in the future')
                
                if self.ENRDATE:
                    age = relativedelta(self.ENRDATE, birth_date).years
                    if age < 16:
                        errors['YEAROFBIRTH'] = _('Patient must be at least 16 years old at enrollment')
                    elif age > 150:
                        errors['YEAROFBIRTH'] = _('Age calculation results in unrealistic age (>150 years)')
                        
            except ValueError:
                errors['DAYOFBIRTH'] = _('Invalid date combination: Day, Month, and Year do not form a valid date')
        
        # Validate that either DOB or age is provided
        has_dob = all([self.DAYOFBIRTH, self.MONTHOFBIRTH, self.YEAROFBIRTH])
        has_age = self.AGEIFDOBUNKNOWN is not None
        
        if not has_dob and not has_age:
            errors['AGEIFDOBUNKNOWN'] = _('Either complete Date of Birth or Age must be provided')
        
        # Validate hospital transfer information
        if self.FROMOTHERHOSPITAL:
            if not self.PRIORHOSPIADMISDATE:
                errors['PRIORHOSPIADMISDATE'] = _('Prior admission date is required when transferred from another hospital')
            elif self.ENRDATE and self.PRIORHOSPIADMISDATE > self.ENRDATE:
                errors['PRIORHOSPIADMISDATE'] = _('Prior admission date cannot be after enrollment date')
        
        # Validate enrollment date is not in future
        if self.ENRDATE and self.ENRDATE > date.today():
            errors['ENRDATE'] = _('Enrollment date cannot be in the future')
        
        # Validate toilet number
        if self.TOILETNUM is not None and self.TOILETNUM < 0:
            errors['TOILETNUM'] = _('Number of toilets cannot be negative')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to clear cache and auto-set fields"""
        # Clear cached properties
        if hasattr(self, '_calculated_age'):
            del self._calculated_age
        if hasattr(self, '_SITEID'):
            del self._SITEID
        
        # Auto-set UNDERLYINGCONDS flag
        if self.pk:
            try:
                underlying = self.Underlying_Condition
                self.UNDERLYINGCONDS = underlying.has_any_condition if underlying else False
            except:
                pass
        
        super().save(*args, **kwargs)