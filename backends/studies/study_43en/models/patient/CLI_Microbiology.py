from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class CLI_Microbiology(models.Model):
    """
    Microbiology culture results for patients
    Tracks specimen types and culture outcomes (Clinical CRF)
    """
    
    # Choices definitions using TextChoices
    class SpecimenTypeChoices(models.TextChoices):
        BLOOD = 'BLOOD', _('Blood')
        URINE = 'URINE', _('Urine')
        PLEURAL_FLUID = 'PLEURAL_FLUID', _('Peritoneal Fluid')
        PERITONEAL_FLUID = 'PERITONEAL_FLUID', _('Pleural Fluid')
        PUS = 'PUS', _('Sputum')
        BRONCHIAL = 'BRONCHIAL', _('Bronchial Lavage')
        CSF = 'CSF', _('Cerebrospinal Fluid')
        WOUND = 'WOUND', _('Wound Discharge')
        OTHER = 'OTHER', _('Other')
    
    class ResultTypeChoices(models.TextChoices):
        POSITIVE = 'POSITIVE', _('Positive')
        NEGATIVE = 'NEGATIVE', _('Negative')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('EnrollmentCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='microbiology_cultures',
        verbose_name=_('Patient ID')
    )
    
    SPECIMENTYPE = models.CharField(
        max_length=20,
        choices=SpecimenTypeChoices.choices,
        db_index=True,
        verbose_name=_('Specimen Type')
    )
    
    OTHERSPECIMEN = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Other Specimen Type')
    )
    
    PERFORMEDDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Performance Date')
    )
    
    SPECIMENID = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Specimen ID (SID)')
    )
    
    RESULT = models.CharField(
        max_length=20,
        choices=ResultTypeChoices.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Culture Result')
    )
    
    RESULTDETAILS = models.CharField(
        max_length=455,
        blank=True,
        null=True,
        verbose_name=_('Result Details')
    )
    
    SEQUENCE = models.IntegerField(
        default=1,
        verbose_name=_('Sequence Number')
    )
    
    ORDEREDBYDEPT = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Ordering Department')
    )
    
    DEPTDIAGSENT = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Department Diagnosis')
    )
    
    BACSTRAINISOLDATE = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Bacterial Isolation Date')
    )
    
    COMPLETEDBY = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Completed By')
    )
    
    COMPLETEDDATE = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Completion Date')
    )
    
    # Metadata
    CREATED_AT = models.DateTimeField(auto_now_add=True)
    CREATEDAT = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CLI_Microbiology'
        verbose_name = _('Microbiology Culture')
        verbose_name_plural = _('Microbiology Cultures')
        unique_together = ['USUBJID', 'SPECIMENTYPE', 'SEQUENCE']
        ordering = ['USUBJID', 'SPECIMENTYPE', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'RESULT'], name='idx_mc_subj_result'),
            models.Index(fields=['PERFORMEDDATE'], name='idx_mc_date'),
            models.Index(fields=['SPECIMENTYPE', 'RESULT'], name='idx_mc_spec_result'),
        ]

    def save(self, *args, **kwargs):
        """Auto-generate SEQUENCE if not provided"""
        if not self.SEQUENCE:
            last_seq = (
                CLI_Microbiology.objects
                .filter(USUBJID=self.USUBJID, SPECIMENTYPE=self.SPECIMENTYPE)
                .aggregate(models.Max('SEQUENCE'))['SEQUENCE__max']
            )
            self.SEQUENCE = (last_seq or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        specimen_display = self.get_SPECIMENTYPE_display()
        return f"{specimen_display} - {self.USUBJID_id} - #{self.SEQUENCE}"

    def is_positive(self):
        """Check if culture result is positive"""
        return self.RESULT == self.ResultTypeChoices.POSITIVE