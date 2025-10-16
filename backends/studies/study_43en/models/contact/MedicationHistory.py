from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ContactMedicationHistory28(models.Model):
    """Medication history for contact follow-up at Day 28"""
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key to ContactFollowUp28
    USUBJID = models.ForeignKey('ContactFollowUp28',
        on_delete=models.CASCADE,
        related_name='medications',
        db_column='USUBJID',
        verbose_name=_('Follow-up Day 28')
    )
    
    EPISODE = models.IntegerField(
        default=1,
        verbose_name=_('Episode Number')
    )
    
    # Medication details
    MEDICATIONNAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Medication Name')
    )
    
    DOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Dosage')
    )
    
    USAGE_PERIOD = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Usage Period')
    )
    
    REASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Usage Reason')
    )
    
    # Metadata
    CREATEDAT = models.DateTimeField(auto_now_add=True)
    UPDATEDAT = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Contact_Medication_history_28'
        verbose_name = _('Contact Medication History (Day 28)')
        verbose_name_plural = _('Contact Medication Histories (Day 28)')
        unique_together = ['USUBJID', 'EPISODE']
        ordering = ['EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_cmh28_subj_ep'),
        ]
    
    def __str__(self):
        return f"Medication Episode {self.EPISODE} ({self.MEDICATIONNAME}) - {self.USUBJID}"


class ContactMedicationHistory90(models.Model):
    """Medication history for contact follow-up at Day 90"""
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key to ContactFollowUp90
    USUBJID = models.ForeignKey('ContactFollowUp90',
        on_delete=models.CASCADE,
        related_name='medications',
        db_column='USUBJID',
        verbose_name=_('Follow-up Day 90')
    )
    
    EPISODE = models.IntegerField(
        default=1,
        verbose_name=_('Episode Number')
    )
    
    # Medication details
    MEDICATIONNAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Medication Name')
    )
    
    DOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Dosage')
    )
    
    USAGE_PERIOD = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Usage Period')
    )
    
    REASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Usage Reason')
    )
    
    # Metadata
    CREATEDAT = models.DateTimeField(auto_now_add=True)
    UPDATEDAT = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Contact_Medication_history_90'
        verbose_name = _('Contact Medication History (Day 90)')
        verbose_name_plural = _('Contact Medication Histories (Day 90)')
        unique_together = ['USUBJID', 'EPISODE']
        ordering = ['EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_cmh90_subj_ep'),
        ]
    
    def __str__(self):
        return f"Medication Episode {self.EPISODE} ({self.MEDICATIONNAME}) - {self.USUBJID} (Day 90)"