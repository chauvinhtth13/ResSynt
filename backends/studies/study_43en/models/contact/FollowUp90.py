from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ContactFollowUp90(models.Model):
    """Contact follow-up at Day 90"""
    
    # Choices definitions using TextChoices
    class AssessedChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key
    USUBJID = models.OneToOneField('EnrollmentContact',
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='USUBJID',
        verbose_name=_('Contact')
    )
    
    # Assessment
    ASSESSED = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Assessed at Day 90')
    )
    
    ASSESSDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Assessment Date')
    )
    
    # Healthcare exposure since last visit
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
    
    HOMEWOUNDCARE = models.BooleanField(
        default=False,
        verbose_name=_('Home Wound Care')
    )
    
    LONGTERMCAREFACILITY = models.BooleanField(
        default=False,
        verbose_name=_('Long-term Care Facility')
    )
    
    # Medication use
    MEDICATIONUSE = models.BooleanField(
        default=False,
        verbose_name=_('Medication Use (corticoid, PPI, antibiotics)')
    )
    
    # Completion
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
    CREATEDAT = models.DateTimeField(auto_now_add=True)
    UPDATEDAT = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Contact_FU_Case_90'
        verbose_name = _('Contact Follow-up Day 90')
        verbose_name_plural = _('Contact Follow-ups Day 90')
    
    def __str__(self):
        return f"Follow-up 90 - {self.USUBJID}"