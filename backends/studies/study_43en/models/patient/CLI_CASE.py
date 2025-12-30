from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.functional import cached_property
from django.db import transaction
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date
class CLI_CASE(AuditFieldsMixin):
    """
    Clinical information for enrolled patients
    Optimizations:
    - Added AuditFieldsMixin for compliance
    - Removed JSONField symptoms (use 1-1 models instead)
    - Added comprehensive validation
    - Cached properties for computed values
    - Better indexes for queries
    """

    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class ThreeStateChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        UNKNOWN = 'unknown', _('Unknown')

    class InfectFocus48HChoices(models.TextChoices):
        ABD_ABSCESS = 'AbdAbscess', _('Abdominal Abscess')
        EMPYEMA = 'Empyema', _('Empyema')
        MENINGITIS = 'Meningitis', _('Meningitis')
        NTTKTW = 'NTTKTW', _('NTTKTW')
        PERITONITIS = 'Peritonitis', _('Peritonitis')
        OSTEOMYELITIS = 'Osteomyelitis', _('Osteomyelitis')
        OTHER = 'Other', _('Other')
        PNEUMONIA = 'Pneumonia', _('Pneumonia/Lung Abscess')
        SOFT_TISSUE = 'SoftTissue', _('Skin/Soft Tissue')
        UNKNOWN = 'Unk', _('Unknown')
        UTI = 'UTI', _('Urinary Tract Infection')

    class InfectSrcChoices(models.TextChoices):
        COMMUNITY = 'Community', _('Community-Acquired')
        HEALTHCARE_ASSOCIATED = 'HealthcareAssociated', _('Healthcare-Associated')

    class SupportTypeChoices(models.TextChoices):
        OXY_MASK = 'Oxy mũi/mask', _('Nasal Cannula/Mask')
        HFNC_NIV = 'HFNC/NIV', _('HFNC/NIV')
        VENTILATOR = 'Thở máy', _('Mechanical Ventilation')

    class FluidChoices(models.TextChoices):
        CRYSTAL = 'Crystal', _('Crystalloid')
        COLLOID = 'Colloid', _('Colloid')

    class DrainageTypeChoices(models.TextChoices):
        ABSCESS = 'Abscess', _('Abscess')
        EMPYEMA = 'Empyema', _('Empyema')
        OTHER = 'Other', _('Other')

    # ==========================================
    # MANAGERS
    # ==========================================
        

    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='clinical_case',
        verbose_name=_('Patient ID')
    )

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    EVENT = models.CharField(
        max_length=50,
        default='CASE',
        verbose_name=_('Event')
    )

    # ==========================================
    # ADMISSION INFORMATION
    # ==========================================
    ADMISDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Admission Date')
    )

    ADMISREASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Admission')
    )

    SYMPTOMONSETDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Symptom Onset Date')
    )

    ADMISDEPT = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,  # For department analytics
        verbose_name=_('Admission Department')
    )

    OUTPATIENT_ERDEPT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Outpatient/Emergency Department')
    )

    SYMPTOMADMISDEPT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Admitting Department')
    )

    # ==========================================
    # CONSCIOUSNESS ASSESSMENT
    # ==========================================
    AWARENESS = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Consciousness')
    )

    GCS = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(3), MaxValueValidator(15)],
        verbose_name=_('Glasgow Coma Scale (3-15)')
    )

    EYES = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        verbose_name=_('Eye Opening Response (1-4)')
    )

    MOTOR = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name=_('Motor Response (1-6)')
    )

    VERBAL = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Verbal Response (1-5)')
    )

    # ==========================================
    # VITAL SIGNS
    # ==========================================
    PULSE = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(300)],
        verbose_name=_('Heart Rate ((beats/min)')
    )

    AMPLITUDE = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Pulse Amplitude')
    )

    CAPILLARYMOIS = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Capillary Moisture')
    )

    CRT = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Capillary Refill Time (seconds)')
    )

    TEMPERATURE = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(45)],
        verbose_name=_('Temperature (°C)')
    )

    BLOODPRESSURE_SYS = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(40), MaxValueValidator(250)],
        verbose_name=_('Systolic BP (mmHg)')
    )

    BLOODPRESSURE_DIAS = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(20), MaxValueValidator(150)],
        verbose_name=_('Diastolic BP (mmHg)')
    )

    RESPRATE = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Respiratory rate (breaths/min)')
    )

    SPO2 = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('SpO2 (%)')
    )

    FIO2 = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(21), MaxValueValidator(100)],
        verbose_name=_('FiO2 (%)')
    )

    # ==========================================
    # RESPIRATORY PATTERN
    # ==========================================
    RESPPATTERN = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Respiratory Pattern')
    )

    RESPPATTERNOTHERSPEC = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Respiratory Pattern Details')
    )

    RESPSUPPORT = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Respiratory Support')
    )

    # ==========================================
    # CLINICAL SCORES
    # ==========================================
    VASOMEDS = models.BooleanField(
        default=False,
        verbose_name=_('Vasopressors')
    )

    HYPOTENSION = models.BooleanField(
        default=False,
        verbose_name=_('Is there hypotension?')
    )

    QSOFA = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        verbose_name=_('qSOFA Score (0-3)')
    )

    NEWS2 = models.CharField(
        max_length=10,
        choices=[
            ('low', _('0-4 Low')),
            ('medium', _('5-6 Medium')),
            ('high', _('≥7 High')),
        ],
        null=True,
        blank=True,
        verbose_name=_('NEWS2 Score (0-20)')
    )

    # ==========================================
    # PHYSICAL MEASUREMENTS
    # ==========================================
    WEIGHT = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
        verbose_name=_('Weight (kg)')
    )

    HEIGHT = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(50), MaxValueValidator(250)],
        verbose_name=_('Height (cm)')
    )

    BMI = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(60)],
        verbose_name=_('Body Mass Index')
    )

    TOTALCULTURERES = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Total Culture Results')
    )

    # ==========================================
    # INFECTION INFORMATION
    # ==========================================
    INFECTFOCUS48H = models.CharField(
        max_length=50,
        choices=InfectFocus48HChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Infection Site (identified within the first 48h of admission)?')
    )

    SPECIFYOTHERINFECT48H = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other, specify')
    )

    BLOODINFECT = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Bloodstream infection?')
    )

    SOFABASELINE = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        verbose_name=_('Background SOFA score')
    )

    DIAGSOFA = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        verbose_name=_('SOFA score at diagnosis')
    )

    SEPTICSHOCK = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        db_index=True,  # For severity analysis
        verbose_name=_('Septic Shock?')
    )

    INFECTSRC = models.CharField(
        max_length=50,
        choices=InfectSrcChoices.choices,
        null=True,
        blank=True,
        db_index=True,  # For epidemiology
        verbose_name=_('Infection source?')
    )

    # ==========================================
    # RESPIRATORY SUPPORT
    # ==========================================
    RESPISUPPORT = models.BooleanField(
        default=False,
        verbose_name=_('Respiratory support?')
    )

    OXYMASKDURATION = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Nasal O2/mask, duration (days)')
    )

    HFNCNIVDURATION = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('HFNC/NIV, duration (days)')
    )

    VENTILATORDURATION = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Mechanical ventilation, duration (days)')
    )

    # ==========================================
    # FLUID RESUSCITATION
    # ==========================================
    RESUSFLUID = models.BooleanField(
        default=False,
        verbose_name=_('Resuscitation fluids?')
    )

    FLUID6HOURS = models.CharField(
        max_length=50,
        choices=FluidChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Total fluid infusion in the first 6 hours')
    )

    CRYSTAL6HRS = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Crystalloid (ml)')
    )

    COL6HRS = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Colloid (ml)')
    )

    FLUID24HOURS = models.CharField(
        max_length=50,
        choices=FluidChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Total fluid infusion in the first 24 hours')
    )

    CRYSTAL24HRS = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Crystalloid')
    )

    COL24HRS = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Colloid')
    )

    # ==========================================
    # OTHER TREATMENTS
    # ==========================================
    VASOINOTROPES = models.BooleanField(
        default=False,
        verbose_name=_('Vasomotor/increased myocardial contractility?')
    )

    DIALYSIS = models.BooleanField(
        default=False,
        verbose_name=_('Blood filtration?')
    )

    DRAINAGE = models.BooleanField(
        default=False,
        verbose_name=_('Drainage?')
    )

    DRAINAGETYPE = models.CharField(
        max_length=50,
        choices=DrainageTypeChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Drainage Type')
    )

    SPECIFYOTHERDRAINAGE = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other, specify')
    )

    # ==========================================
    # ANTIBIOTIC INFORMATION
    # ==========================================
    PRIORANTIBIOTIC = models.BooleanField(
        default=False,
        verbose_name=_('Prior Antibiotic Use')
    )

    INITIALANTIBIOTIC = models.BooleanField(
        default=False,
        verbose_name=_('Initial Antibiotic Given')
    )

    INITIALABXAPPROP = models.BooleanField(
        default=False,
        verbose_name=_('Initial Antibiotic Appropriate')
    )


    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_CASE'
        verbose_name = _('Clinical Case')
        verbose_name_plural = _('Clinical Cases')
        ordering = ['-ADMISDATE']
        indexes = [
            models.Index(fields=['ADMISDATE'], name='idx_clin_admis'),
            models.Index(fields=['INFECTFOCUS48H'], name='idx_clin_infect'),
            models.Index(fields=['SEPTICSHOCK', 'ADMISDATE'], name='idx_clin_severity'),
            models.Index(fields=['INFECTSRC', 'ADMISDATE'], name='idx_clin_source'),
            models.Index(fields=['ADMISDEPT'], name='idx_clin_dept'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_clin_modified'),
        ]
        constraints = [
            # GCS must equal sum of components
            models.CheckConstraint(
                condition=(
                    models.Q(GCS__isnull=True) |
                    models.Q(EYES__isnull=True) |
                    models.Q(MOTOR__isnull=True) |
                    models.Q(VERBAL__isnull=True) |
                    models.Q(GCS=models.F('EYES') + models.F('MOTOR') + models.F('VERBAL'))
                ),
                name='clin_gcs_sum_check'
            ),
            # Diastolic must be less than systolic
            models.CheckConstraint(
                condition=(
                    models.Q(BLOODPRESSURE_SYS__isnull=True) |
                    models.Q(BLOODPRESSURE_DIAS__isnull=True) |
                    models.Q(BLOODPRESSURE_DIAS__lt=models.F('BLOODPRESSURE_SYS'))
                ),
                name='clin_bp_dias_lt_sys'
            ),
            # If drainage performed, type must be specified
            models.CheckConstraint(
                condition=(
                    ~models.Q(DRAINAGE=True) |
                    models.Q(DRAINAGETYPE__isnull=False)
                ),
                name='clin_drainage_type_required'
            ),
            # If other infection, must specify
            models.CheckConstraint(
                condition=(
                    ~models.Q(INFECTFOCUS48H='Other') |
                    models.Q(SPECIFYOTHERINFECT48H__isnull=False)
                ),
                name='clin_specify_other_infection'
            ),
            # Symptom onset must be before or on admission
            models.CheckConstraint(
                condition=(
                    models.Q(SYMPTOMONSETDATE__isnull=True) |
                    models.Q(ADMISDATE__isnull=True) |
                    models.Q(SYMPTOMONSETDATE__lte=models.F('ADMISDATE'))
                ),
                name='clin_symptom_before_admission'
            ),
        ]

    def __str__(self):
        return f"Clinical: {self.USUBJID_id}"

    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None

    @cached_property
    def calculated_bmi(self):
        """Calculate BMI from weight and height"""
        if self.WEIGHT and self.HEIGHT:
            height_m = self.HEIGHT / 100  # Convert cm to m
            return round(self.WEIGHT / (height_m ** 2), 2)
        return None

    @cached_property
    def calculated_gcs(self):
        """Calculate GCS from components"""
        if all([self.EYES, self.MOTOR, self.VERBAL]):
            return self.EYES + self.MOTOR + self.VERBAL
        return None

    @cached_property
    def is_severe_sepsis(self):
        """Check if patient has severe sepsis (SOFA increase ≥2)"""
        if self.SOFABASELINE is not None and self.DIAGSOFA is not None:
            return (self.DIAGSOFA - self.SOFABASELINE) >= 2
        return None

    @cached_property
    def symptom_to_admission_days(self):
        """Days from symptom onset to admission"""
        if self.SYMPTOMONSETDATE and self.ADMISDATE:
            delta = self.ADMISDATE - self.SYMPTOMONSETDATE
            return delta.days
        return None

    @cached_property
    def total_respiratory_support_days(self):
        """Total days of any respiratory support"""
        days = 0
        if self.OXYMASKDURATION:
            days += self.OXYMASKDURATION
        if self.HFNCNIVDURATION:
            days += self.HFNCNIVDURATION
        if self.VENTILATORDURATION:
            days += self.VENTILATORDURATION
        return days if days > 0 else None

    @cached_property
    def has_history_symptoms(self):
        """Check if HistorySymptom record exists"""
        return hasattr(self, 'History_Symptom')

    @cached_property
    def has_72h_symptoms(self):
        """Check if Symptom_72H record exists"""
        return hasattr(self, 'Symptom_72H')

    # ==========================================
    # INFECTION FOCUS PROPERTIES
    # ==========================================
    @property
    def is_AbdAbscess(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.ABD_ABSCESS

    @property
    def is_Pneumonia(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.PNEUMONIA

    @property
    def is_UTI(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.UTI

    @property
    def is_Meningitis(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.MENINGITIS

    # ==========================================
    # CLINICAL STATUS PROPERTIES
    # ==========================================
    @property
    def has_bloodstream_infection(self):
        return self.BLOODINFECT == self.ThreeStateChoices.YES

    @property
    def has_septic_shock(self):
        return self.SEPTICSHOCK == self.ThreeStateChoices.YES

    @property
    def is_community_acquired(self):
        return self.INFECTSRC == self.InfectSrcChoices.COMMUNITY

    @property
    def is_healthcare_associated(self):
        return self.INFECTSRC == self.InfectSrcChoices.HEALTHCARE_ASSOCIATED

    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Validate GCS components
        if self.GCS and all([self.EYES, self.MOTOR, self.VERBAL]):
            calculated = self.EYES + self.MOTOR + self.VERBAL
            if self.GCS != calculated:
                errors['GCS'] = _(
                    f'GCS ({self.GCS}) must equal sum of components ({calculated})'
                )
        
        # Validate blood pressure
        if self.BLOODPRESSURE_SYS and self.BLOODPRESSURE_DIAS:
            if self.BLOODPRESSURE_DIAS >= self.BLOODPRESSURE_SYS:
                errors['BLOODPRESSURE_DIAS'] = _(
                    'Diastolic BP must be less than Systolic BP'
                )
        
        # Validate drainage
        if self.DRAINAGE:
            if not self.DRAINAGETYPE:
                errors['DRAINAGETYPE'] = _(
                    'Drainage type must be specified when drainage is performed'
                )
            if self.DRAINAGETYPE == self.DrainageTypeChoices.OTHER and not self.SPECIFYOTHERDRAINAGE:
                errors['SPECIFYOTHERDRAINAGE'] = _(
                    'Please specify other drainage type'
                )
        
        # Validate infection focus
        if self.INFECTFOCUS48H == self.InfectFocus48HChoices.OTHER:
            if not self.SPECIFYOTHERINFECT48H or not self.SPECIFYOTHERINFECT48H.strip():
                errors['SPECIFYOTHERINFECT48H'] = _(
                    'Please specify other infection focus'
                )
        
        # Validate dates
        if self.SYMPTOMONSETDATE and self.ADMISDATE:
            if self.SYMPTOMONSETDATE > self.ADMISDATE:
                errors['SYMPTOMONSETDATE'] = _(
                    'Symptom onset date cannot be after admission date'
                )
        
        if self.ADMISDATE and self.ADMISDATE > date.today():
            errors['ADMISDATE'] = _('Admission date cannot be in the future')
        
        # Validate BMI if both weight and height provided
        if self.WEIGHT and self.HEIGHT and self.BMI:
            calculated_bmi = self.calculated_bmi
            if calculated_bmi and abs(self.BMI - calculated_bmi) > 0.5:
                errors['BMI'] = _(
                    f'BMI ({self.BMI}) does not match calculated value ({calculated_bmi})'
                )
        
        # Validate SOFA scores
        if self.SOFABASELINE and self.DIAGSOFA:
            if self.DIAGSOFA < self.SOFABASELINE:
                errors['DIAGSOFA'] = _(
                    'Diagnosis SOFA score should not be less than baseline'
                )
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save with auto-calculations and cache management"""
        # Clear cached properties
        self._clear_cache()
        
        # Auto-calculate BMI if not provided
        if self.WEIGHT and self.HEIGHT and not self.BMI:
            self.BMI = self.calculated_bmi
        
        # Auto-calculate GCS if not provided
        if all([self.EYES, self.MOTOR, self.VERBAL]) and not self.GCS:
            self.GCS = self.calculated_gcs
        
        # Strip whitespace from text fields
        text_fields = [
            'ADMISREASON', 'SYMPTOMADMISDEPT', 'AWARENESS',
            'RESPPATTERNOTHERSPEC', 'SPECIFYOTHERINFECT48H',
            'SPECIFYOTHERDRAINAGE'
        ]
        for field in text_fields:
            value = getattr(self, field)
            if value:
                setattr(self, field, value.strip())
        
        super().save(*args, **kwargs)

    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_calculated_bmi', '_calculated_gcs',
            '_is_severe_sepsis', '_symptom_to_admission_days',
            '_total_respiratory_support_days',
            '_has_history_symptoms', '_has_72h_symptoms'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)

    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_by_infection_focus(cls, focus):
        """Get cases by infection focus"""
        return cls.objects.filter(INFECTFOCUS48H=focus).select_related('USUBJID')

    @classmethod
    def get_severe_cases(cls):
        """Get cases with septic shock or high SOFA"""
        return cls.objects.filter(
            models.Q(SEPTICSHOCK=cls.ThreeStateChoices.YES) |
            models.Q(DIAGSOFA__gte=10)
        ).select_related('USUBJID')

    @classmethod
    def get_with_complete_data(cls):
        """Get cases with both symptom assessments"""
        return cls.objects.filter(
            History_Symptom__isnull=False,
            Symptom_72H__isnull=False
        ).select_related('USUBJID', 'History_Symptom', 'Symptom_72H')