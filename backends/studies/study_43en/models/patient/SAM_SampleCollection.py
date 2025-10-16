from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class SampleCollection(models.Model):
    """
    Sample collection tracking for patients
    Records various biological samples collected at different time points
    """
    
    # Choices definitions using TextChoices
    class SampleTypeChoices(models.TextChoices):
        SAMPLE1 = '1', _('Sample 1 (At enrollment)')
        SAMPLE2 = '2', _('Sample 2 (10 ± 3 days after enrollment)')
        SAMPLE3 = '3', _('Sample 3 (28 ± 3 days after enrollment)')
        SAMPLE4 = '4', _('Sample 4 (90 ± 3 days after enrollment)')
    
    class CultureResultChoices(models.TextChoices):
        POSITIVE = 'Pos', _('Positive')
        NEGATIVE = 'Neg', _('Negative')
        NO_APPLY = 'NoApply', _('Not Applicable')
        NOT_PERFORMED = 'NotPerformed', _('Not Performed')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('EnrollmentCase',
        to_field='USUBJID',
        on_delete=models.CASCADE,
        related_name='sample_collections',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    SAMPLE_TYPE = models.CharField(
        max_length=1,
        choices=SampleTypeChoices.choices,
        db_index=True,
        verbose_name=_('Sample Type')
    )
    
    # Sample collection status
    SAMPLE = models.BooleanField(
        default=True,
        verbose_name=_('Sample Collected')
    )
    
    # Sample types
    STOOL = models.BooleanField(
        default=False,
        verbose_name=_('Stool Sample')
    )
    
    STOOLDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Stool Collection Date')
    )
    
    RECTSWAB = models.BooleanField(
        default=False,
        verbose_name=_('Rectal Swab')
    )
    
    RECTSWABDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Rectal Swab Date')
    )
    
    THROATSWAB = models.BooleanField(
        default=False,
        verbose_name=_('Throat Swab')
    )
    
    THROATSWABDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Throat Swab Date')
    )
    
    BLOOD = models.BooleanField(
        default=False,
        verbose_name=_('Blood Sample')
    )
    
    BLOODDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Blood Collection Date')
    )
    
    REASONIFNO = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason if Not Collected')
    )
    
    # Culture results - Stool
    CULTRES_1 = models.CharField(
        max_length=20,
        choices=CultureResultChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Stool Culture Result')
    )
    
    KLEBPNEU_1 = models.BooleanField(
        default=False,
        verbose_name=_('Klebsiella pneumoniae (Stool)')
    )
    
    OTHERRES_1 = models.BooleanField(
        default=False,
        verbose_name=_('Other (Stool)')
    )
    
    OTHERRESSPECIFY_1 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Specify (Stool)')
    )
    
    # Culture results - Rectal swab
    CULTRES_2 = models.CharField(
        max_length=20,
        choices=CultureResultChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Rectal Swab Culture Result')
    )
    
    KLEBPNEU_2 = models.BooleanField(
        default=False,
        verbose_name=_('Klebsiella pneumoniae (Rectal)')
    )
    
    OTHERRES_2 = models.BooleanField(
        default=False,
        verbose_name=_('Other (Rectal)')
    )
    
    OTHERRESSPECIFY_2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Specify (Rectal)')
    )
    
    # Culture results - Throat swab
    CULTRES_3 = models.CharField(
        max_length=20,
        choices=CultureResultChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Throat Swab Culture Result')
    )
    
    KLEBPNEU_3 = models.BooleanField(
        default=False,
        verbose_name=_('Klebsiella pneumoniae (Throat)')
    )
    
    OTHERRES_3 = models.BooleanField(
        default=False,
        verbose_name=_('Other (Throat)')
    )
    
    OTHERRESSPECIFY_3 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Specify (Throat)')
    )
    
    # Completion info
    COMPLETEDBY = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Completed By')
    )
    
    COMPLETEDDATE = models.DateField(
        default=timezone.now,
        verbose_name=_('Completion Date')
    )
    
    class Meta:
        db_table = 'SAM_Case'
        verbose_name = _('Sample Collection')
        verbose_name_plural = _('Sample Collections')
        unique_together = ('USUBJID', 'SAMPLE_TYPE')
        ordering = ['USUBJID', 'SAMPLE_TYPE']
        indexes = [
            models.Index(fields=['SAMPLE_TYPE'], name='idx_sc_type'),
            models.Index(fields=['USUBJID', 'SAMPLE_TYPE'], name='idx_sc_subj_type'),
        ]
        
    def __str__(self):
        sample_type_display = self.get_SAMPLE_TYPE_display()
        return f"{sample_type_display} - {self.USUBJID}"