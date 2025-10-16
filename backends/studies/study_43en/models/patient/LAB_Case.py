from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class LAB_Microbiology(models.Model):
    """
    Laboratory microbiology culture results
    Separate from clinical microbiology - used for antibiotic sensitivity testing
    """
    
    # Choices definitions using TextChoices
    class SpecimenLocationChoices(models.TextChoices):
        BLOOD = 'BLOOD', _('Blood')
        URINE = 'URINE', _('Urine')
        PLEURAL_FLUID = 'PLEURAL_FLUID', _('Peritoneal Fluid')
        PERITONEAL_FLUID = 'PERITONEAL_FLUID', _('Pleural Fluid')
        PUS = 'PUS', _('Sputum')
        BRONCHIAL = 'BRONCHIAL', _('Bronchial Lavage')
        CSF = 'CSF', _('Cerebrospinal Fluid')
        WOUND = 'WOUND', _('Wound Discharge')
        OTHER = 'OTHER', _('Other')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Basic information
    EVENT = models.CharField(
        max_length=50,
        default='LAB_CULTURE',
        verbose_name=_('Event')
    )
    
    # Foreign key
    USUBJID = models.ForeignKey('EnrollmentCase',
        to_field='USUBJID',
        on_delete=models.CASCADE,
        related_name='lab_microbiology_cultures',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    LAB_CASE_SEQ = models.IntegerField(
        default=1,
        verbose_name=_('Lab Case Sequence Number')
    )
    
    # Study identifiers
    STUDYIDS = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('Site ID')
    )
    
    SUBJID = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Subject ID')
    )
    
    INITIAL = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Initials')
    )
    
    # Department information
    ORDEREDBYDEPT = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Ordering Department')
    )
    
    DEPTDIAGSENT = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Department Diagnosis')
    )
    
    # Specimen information
    SPECIMENID = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Specimen ID (SID)')
    )
    
    SPECSAMPLOC = models.CharField(
        max_length=20,
        choices=SpecimenLocationChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Specimen Sample Location')
    )
    
    OTHERSPECIMEN = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Other Specimen Type')
    )
    
    SPECSAMPDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Specimen Sample Date')
    )
    
    BACSTRAINISOLDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Bacterial Strain Isolation Date')
    )
    
    # Completion info
    COMPLETEDBY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Completed By')
    )
    
    COMPLETEDDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Completion Date')
    )
    
    # Metadata
    entry = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Entry Number')
    )
    
    enteredtime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Entry Time')
    )
    
    CREATED_AT = models.DateTimeField(auto_now_add=True)
    UPDATED_AT = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LAB_Microbiology'
        verbose_name = _('LAB Microbiology Culture')
        verbose_name_plural = _('LAB Microbiology Cultures')
        unique_together = ['USUBJID', 'LAB_CASE_SEQ']
        ordering = ['USUBJID', 'LAB_CASE_SEQ']
        indexes = [
            models.Index(fields=['USUBJID', 'LAB_CASE_SEQ'], name='idx_lmc_subj_seq'),
            models.Index(fields=['SPECSAMPDATE'], name='idx_lmc_date'),
            models.Index(fields=['SPECSAMPLOC'], name='idx_lmc_spec'),
        ]

    def save(self, *args, **kwargs):
        """Auto-generate LAB_CASE_SEQ if not provided"""
        if not self.LAB_CASE_SEQ:
            last_seq = (
                LAB_Microbiology.objects
                .filter(USUBJID=self.USUBJID)
                .aggregate(models.Max('LAB_CASE_SEQ'))['LAB_CASE_SEQ__max']
            )
            self.LAB_CASE_SEQ = (last_seq or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        specimen_display = self.get_SPECSAMPLOC_display() if self.SPECSAMPLOC else 'Unknown'
        return f"LAB Culture - {specimen_display} - {self.USUBJID_id} - #{self.LAB_CASE_SEQ}"

    def get_sensitivity_count(self):
        """Count number of antibiotic sensitivity results"""
        return self.antibiotic_sensitivities.count()
    
    def get_sensitivity_by_tier(self):
        """Get antibiotic sensitivity results grouped by tier"""
        from study_43en.models.patient import LAB_AntibioticSensitivity
        
        results = {}
        for tier_value, _ in LAB_AntibioticSensitivity.TierChoices.choices:
            sensitivities = self.antibiotic_sensitivities.filter(TIER=tier_value).order_by('SEQUENCE')
            results[tier_value] = list(sensitivities)
        
        return results