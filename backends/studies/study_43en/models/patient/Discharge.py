from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class DischargeCase(models.Model):
    """
    Hospital discharge information
    Records discharge status, transfers, and outcomes
    """
    
    # Choices definitions using TextChoices
    class DischargeStatusChoices(models.TextChoices):
        RECOVERED = 'Recovered', _('Discharged - Fully Recovered')
        IMPROVED = 'Improved', _('Discharged - Not Fully Recovered')
        DIED = 'Died', _('Death or Moribund')
        TRANSFERRED_LEFT = 'TransferredLeft', _('Transferred/Left Against Medical Advice')
    
    class TransferChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with EnrollmentCase
    USUBJID = models.OneToOneField('EnrollmentCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    # Header information
    EVENT = models.CharField(
        max_length=50,
        default='DISCHARGE',
        verbose_name=_('Event')
    )
    
    STUDYID = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        verbose_name=_('Site ID')
    )
    
    SUBJID = models.CharField(
        max_length=10,
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
    
    # 1. Discharge date
    DISCHDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('1. Discharge Date')
    )
    
    # 3. Discharge status
    DISCHSTATUS = models.CharField(
        max_length=20,
        choices=DischargeStatusChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('3. Discharge Status')
    )
    
    DISCHSTATUSDETAIL = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Discharge Status Details')
    )
    
    # 4. Transfer to another hospital?
    TRANSFERHOSP = models.CharField(
        max_length=3,
        choices=TransferChoices.choices,
        default=TransferChoices.NO,
        verbose_name=_('4. Transferred to Another Hospital?')
    )
    
    # 4a. Transfer reason
    TRANSFERREASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('4a. Transfer Reason')
    )
    
    # 4b. Transfer location
    TRANSFERLOCATION = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_('4b. Transfer Location')
    )
    
    # 5. Death at discharge?
    DEATHATDISCH = models.CharField(
        max_length=3,
        choices=TransferChoices.choices,
        default=TransferChoices.NO,
        verbose_name=_('5. Death at Discharge?')
    )
    
    # 5. If Yes, cause of death
    DEATHCAUSE = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('5. If Yes, Cause of Death')
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
    CREATEDDATE = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date')
    )
    
    UPDATEDDATE = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated Date')
    )
    
    class Meta:
        db_table = 'Discharge_Case'
        verbose_name = _('Discharge Case')
        verbose_name_plural = _('Discharge Cases')
        ordering = ['-COMPLETEDDATE']
        indexes = [
            models.Index(fields=['DISCHDATE'], name='idx_dc_date'),
            models.Index(fields=['DISCHSTATUS'], name='idx_dc_status'),
        ]
    
    def __str__(self):
        return f"Discharge - {self.USUBJID}"
    
    @property
    def has_death_info(self):
        """Check if death information is present"""
        return self.DEATHATDISCH == self.TransferChoices.YES and self.DEATHCAUSE
    
    @property
    def has_transfer_info(self):
        """Check if transfer information is present"""
        return self.TRANSFERHOSP == self.TransferChoices.YES and (self.TRANSFERREASON or self.TRANSFERLOCATION)
    
    def save(self, *args, **kwargs):
        """Auto-populate fields from ScreeningCase if needed"""
        if self.USUBJID:
            screening = self.USUBJID
            if not self.STUDYID:
                self.STUDYID = screening.STUDYID
            if not self.SITEID:
                self.SITEID = screening.SITEID
            if not self.SUBJID:
                self.SUBJID = screening.SUBJID
            if not self.INITIAL:
                self.INITIAL = screening.INITIAL
        
        super().save(*args, **kwargs)


class DischargeICD(models.Model):
    """
    ICD-10 codes at discharge
    Multiple diagnosis codes can be assigned per discharge
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('DischargeCase',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='icd_codes',
        verbose_name=_('Discharge Case')
    )
    
    # ICD sequence (1-6)
    ICD_SEQUENCE = models.IntegerField(
        default=1,
        verbose_name=_('ICD Sequence Number')
    )
    
    # 2. Discharge diagnosis - ICD-10 code
    ICDCODE = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('ICD-10 Code')
    )
    
    ICDDETAIL = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Diagnosis Details')
    )
    
    class Meta:
        db_table = 'discharge_icd'
        verbose_name = _('Discharge ICD Code')
        verbose_name_plural = _('Discharge ICD Codes')
        unique_together = ['USUBJID', 'ICD_SEQUENCE']
        ordering = ['ICD_SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'ICD_SEQUENCE'], name='idx_dicd_subj_ep'),
            models.Index(fields=['ICDCODE'], name='idx_dicd_code'),
        ]
    
    def __str__(self):
        return f"ICD-10.{self.ICD_SEQUENCE}: {self.ICDCODE} - {self.USUBJID.USUBJID}"