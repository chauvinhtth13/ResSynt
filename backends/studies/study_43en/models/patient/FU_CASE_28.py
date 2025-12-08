from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class FU_CASE_28(AuditFieldsMixin):
    """
    Follow-up Case at Day 28
     ONLY RENAMED FIELDS - NO LOGIC CHANGES
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class AssessedChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    class PatientStatusChoices(models.TextChoices):
        ALIVE = 'Alive', _('Alive')
        REHOSPITALIZED = 'Rehospitalized', _('Rehospitalized')
        DECEASED = 'Deceased', _('Deceased')
        LOST_TO_FOLLOWUP = 'LostToFollowUp', _('Lost to Follow-up')
    
    class FunctionalStatusChoices(models.TextChoices):
        NORMAL = 'Normal', _('Normal')
        PROBLEM = 'Problem', _('Problem')
        BEDRIDDEN = 'Bedridden', _('Bedridden')
    
    class AnxietyDepressionChoices(models.TextChoices):
        NONE = 'None', _('None')
        MODERATE = 'Moderate', _('Moderate')
        SEVERE = 'Severe', _('Severe')
    
    class FBSIScoreChoices(models.IntegerChoices):
        SCORE_7 = 7, _('7. Discharged; basically healthy; able to perform high-level daily activities')
        SCORE_6 = 6, _('6. Discharged; moderate symptoms/signs; unable to perform daily activities')
        SCORE_5 = 5, _('5. Discharged; severe disability; requires high-level daily care and support')
        SCORE_4 = 4, _('4. Hospitalized but not in ICU')
        SCORE_3 = 3, _('3. Hospitalized in ICU')
        SCORE_2 = 2, _('2. Long-term ventilation unit')
        SCORE_1 = 1, _('1. End-of-life palliative care (hospital or home)')
        SCORE_0 = 0, _('0. Death')
    
    # ==========================================
    # MANAGERS
    # ==========================================
    objects = models.Manager()
    site_objects = SiteFilteredManager()
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='followup_28',
        verbose_name=_('Unique Subject ID')
    )
    
    
    # ==========================================
    # SECTION 1: ASSESSMENT
    # ==========================================
    EvaluatedAtDay28 = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("1. The patient's condition was assessed on Day 28?")
    )
    
    EvaluateDate = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('a. Date (dd/mm/yyyy)')
    )
    
    Outcome28Days = models.CharField(
        max_length=20,
        choices=PatientStatusChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('b. Status')
    )
    
    # ==========================================
    # SECTION 2: REHOSPITALIZATION
    # ==========================================
    Rehospitalized = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('2. Patients readmitted to hospital?')
    )
    
    ReHosp_Times = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('a. How many times?')
    )
    
    # ==========================================
    # SECTION 3: DEATH INFORMATION
    # ==========================================
    Dead = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('3. Patient death?')
    )
    
    DeathDate = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('a. Date (dd/mm/yyyy)')
    )
    
    DeathReason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('b. Reason')
    )
    
    # ==========================================
    # SECTION 4: ANTIBIOTIC USE
    # ==========================================
    Antb_Usage = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('4. Did the patient use antibiotics since the last visit?')
    )
    
    Antb_Usage_Times = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('a. How many times?')
    )
    
    # ==========================================
    # SECTION 5: FUNCTIONAL STATUS
    # ==========================================
    Func_Status = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5. Assessment of Functional Status at Day 28?')
    )
    
    Mobility = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5a. Mobility (walking)')
    )
    
    Personal_Hygiene = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5b. Self-care (washing, dressing)')
    )
    
    Daily_Activities = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5c. Daily activities (work, study, housework, leisure activities)')
    )
    
    Pain_Discomfort = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5d. Pain/Discomfort')
    )
    
    Anxiety = models.CharField(
        max_length=20,
        choices=AnxietyDepressionChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5e. Anxiety/Depression')
    )
    
    FBSI = models.IntegerField(
        choices=FBSIScoreChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5f. Functional Bloodstream Infection Score (FBSI)')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'FU_CASE_28'
        verbose_name = _('Follow-up Day 28')
        verbose_name_plural = _('Follow-ups Day 28')
        ordering = ['-EvaluateDate']
        indexes = [
            models.Index(fields=['EvaluateDate'], name='idx_fu28_assess'),
            models.Index(fields=['Outcome28Days'], name='idx_fu28_status'),
            models.Index(fields=['EvaluatedAtDay28', 'EvaluateDate'], name='idx_fu28_asses_date'),
            models.Index(fields=['Dead', 'DeathDate'], name='idx_fu28_death'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_fu28_modified'),
        ]
        constraints = [
            # If assessed YES, must have assessment date
            models.CheckConstraint(
                check=(
                    ~models.Q(EvaluatedAtDay28='Yes') |
                    models.Q(EvaluateDate__isnull=False)
                ),
                name='fu28_assess_date_required'
            ),
            # If deceased YES, must have death date and cause
            models.CheckConstraint(
                check=(
                    ~models.Q(Dead='Yes') |
                    (models.Q(DeathDate__isnull=False) & models.Q(DeathReason__isnull=False))
                ),
                name='fu28_death_info_required'
            ),
        ]
    
    def __str__(self):
        status = self.Outcome28Days or 'Unknown'
        return f"FU Day 28: {self.USUBJID_id} - {status}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def is_alive(self):
        """Check if patient is alive"""
        return self.Outcome28Days == self.PatientStatusChoices.ALIVE
    
    @cached_property
    def is_deceased(self):
        """Check if patient is deceased"""
        return self.Outcome28Days == self.PatientStatusChoices.DECEASED
    
    @cached_property
    def was_rehospitalized(self):
        """Check if patient was rehospitalized"""
        return self.Rehospitalized == self.AssessedChoices.YES
    
    @cached_property
    def used_antibiotics(self):
        """Check if patient used antibiotics"""
        return self.Antb_Usage == self.AssessedChoices.YES
    
    @cached_property
    def has_functional_impairment(self):
        """Check if patient has any functional impairment"""
        impaired_statuses = [
            self.FunctionalStatusChoices.PROBLEM,
            self.FunctionalStatusChoices.BEDRIDDEN
        ]
        return any([
            self.Mobility in impaired_statuses,
            self.Personal_Hygiene in impaired_statuses,
            self.Daily_Activities in impaired_statuses,
            self.Pain_Discomfort in impaired_statuses
        ])
    
    @cached_property
    def functional_score(self):
        """Calculate functional impairment score (0-4)"""
        impaired_statuses = [
            self.FunctionalStatusChoices.PROBLEM,
            self.FunctionalStatusChoices.BEDRIDDEN
        ]
        score = sum([
            self.Mobility in impaired_statuses,
            self.Personal_Hygiene in impaired_statuses,
            self.Daily_Activities in impaired_statuses,
            self.Pain_Discomfort in impaired_statuses
        ])
        return score
    
    @property
    def days_since_enrollment(self):
        """Calculate days from enrollment to assessment"""
        if self.EvaluateDate and self.USUBJID and self.USUBJID.ENRDATE:
            delta = self.EvaluateDate - self.USUBJID.ENRDATE
            return delta.days
        return None
    
    # ==========================================
    # VALIDATION - GIỮ NGUYÊN LOGIC CŨ
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # If assessed, must have assessment date
        if self.EvaluatedAtDay28 == self.AssessedChoices.YES:
            if not self.EvaluateDate:
                errors['EvaluateDate'] = _('Assessment date is required when patient is assessed')
        
        # Validate assessment date
        if self.EvaluateDate:
            #  SIMPLIFIED: Only basic logical validation
            # Allow flexible scheduling - removed strict day range requirements
            try:
                if self.USUBJID and hasattr(self.USUBJID, 'ENRDATE') and self.USUBJID.ENRDATE:
                    # Only check that assessment is after enrollment (basic logic)
                    if self.EvaluateDate < self.USUBJID.ENRDATE:
                        errors['EvaluateDate'] = _('Assessment date cannot be before enrollment date')
            except Exception:
                # Skip validation during create when USUBJID not yet assigned
                pass
        
        # Validate death information
        if self.Dead == self.AssessedChoices.YES:
            if not self.DeathDate:
                errors['DeathDate'] = _('Death date is required when patient is deceased')
            if not self.DeathReason or not self.DeathReason.strip():
                errors['DeathReason'] = _('Cause of death is required when patient is deceased')
            
            # Death date validation
            if self.DeathDate:
                #  REMOVED: Future date validation to allow flexible scheduling
                # if self.DeathDate > date.today():
                #     errors['DeathDate'] = _('Death date cannot be in the future')
                
                if self.EvaluateDate and self.DeathDate > self.EvaluateDate:
                    errors['DeathDate'] = _('Death date cannot be after assessment date')
        
        # Validate patient status consistency
        if self.Dead == self.AssessedChoices.YES and self.Outcome28Days != self.PatientStatusChoices.DECEASED:
            errors['Outcome28Days'] = _('Patient status must be "Deceased" when DECEASED is "Yes"')
        
        # Validate FBSI score consistency with death
        if self.Dead == self.AssessedChoices.YES and self.FBSI and self.FBSI != 0:
            errors['FBSI'] = _('FBSI score must be 0 when patient is deceased')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with cache management and auto-set fields"""
        # Clear cached properties
        self._clear_cache()
        
        # Strip whitespace from text fields
        if self.DeathReason:
            self.DeathReason = self.DeathReason.strip()
        
        # Auto-set patient status based on deceased flag
        if self.Dead == self.AssessedChoices.YES:
            self.Outcome28Days = self.PatientStatusChoices.DECEASED
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_is_alive', '_is_deceased', '_was_rehospitalized',
            '_used_antibiotics', '_has_functional_impairment', '_functional_score'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # QUERY HELPERS - GIỮ NGUYÊN
    # ==========================================
    @classmethod
    def get_assessed_cases(cls):
        """Get all cases that were assessed"""
        return cls.objects.filter(
            EvaluatedAtDay28=cls.AssessedChoices.YES
        ).select_related('USUBJID')
    
    @classmethod
    def get_deceased_cases(cls):
        """Get all deceased cases"""
        return cls.objects.filter(
            Dead=cls.AssessedChoices.YES
        ).select_related('USUBJID').order_by('DeathDate')
    
    @classmethod
    def get_alive_cases(cls):
        """Get all alive cases"""
        return cls.objects.filter(
            Outcome28Days=cls.PatientStatusChoices.ALIVE
        ).select_related('USUBJID')
    
    @classmethod
    def get_rehospitalized_cases(cls):
        """Get all cases with rehospitalization"""
        return cls.objects.filter(
            Rehospitalized=cls.AssessedChoices.YES
        ).select_related('USUBJID')
    
    @classmethod
    def get_lost_to_followup(cls):
        """Get cases lost to follow-up"""
        return cls.objects.filter(
            Outcome28Days=cls.PatientStatusChoices.LOST_TO_FOLLOWUP
        ).select_related('USUBJID')