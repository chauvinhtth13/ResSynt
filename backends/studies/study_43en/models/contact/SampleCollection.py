from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ContactSampleCollection(models.Model):
    """
    Contact sample collection tracking
    Only sample types 1, 3, 4 (no sample 2 for contacts)
    """
    
    # Choices definitions using TextChoices
    class SampleTypeChoices(models.TextChoices):
        SAMPLE1 = '1', _('Sample 1 (Baseline)')
        SAMPLE3 = '3', _('Sample 3 (Day 28 ± 3)')
        SAMPLE4 = '4', _('Sample 4 (Day 90 ± 3)')
    
    class CultureResultChoices(models.TextChoices):
        POSITIVE = 'Pos', _('Positive')
        NEGATIVE = 'Neg', _('Negative')
        NO_APPLY = 'NoApply', _('Not Applicable')
        NOT_PERFORMED = 'NotPerformed', _('Not Performed')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('EnrollmentContact',
        on_delete=models.CASCADE,
        related_name='sample_collections',
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Contact')
    )
    
    SAMPLE_TYPE = models.CharField(
        max_length=1,
        choices=SampleTypeChoices.choices,
        verbose_name=_('Sample Type')
    )
    
    # Sample collection status
    SAMPLE = models.BooleanField(
        default=True,
        verbose_name=_('Sample Collected')
    )
    
    REASONIFNO = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason if Not Collected')
    )
    
    # Sample types and dates
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
    
    # Blood sample (only for Type 1)
    BLOOD = models.BooleanField(
        default=False,
        verbose_name=_('Blood Sample')
    )
    
    BLOODDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Blood Collection Date')
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
    
    ENTRY = models.IntegerField(
        null=True,
        blank=True
    )
    
    ENTEREDTIME = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'Contact_Sam_Case'
        verbose_name = _('Contact Sample Collection')
        verbose_name_plural = _('Contact Sample Collections')
        unique_together = ('USUBJID', 'SAMPLE_TYPE')
        indexes = [
            models.Index(fields=['SAMPLE_TYPE'], name='idx_csc_type'),
        ]

    def __str__(self):
        sample_type_display = self.get_SAMPLE_TYPE_display()
        return f"Sample {sample_type_display} - {self.USUBJID}"