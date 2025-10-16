from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class FollowUpAntibiotic(models.Model):
    """
    Antibiotic usage during follow-up period
    Tracks antibiotic courses after initial treatment
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('FollowUpCase',
        on_delete=models.CASCADE,
        related_name='antibiotics',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    EPISODE = models.IntegerField(
        default=1,
        verbose_name=_('Episode Number')
    )
    
    ANTIBIONAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Antibiotic Name')
    )
    
    ANTIBIOREASONFOR = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Use')
    )
    
    ANTIBIODUR = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Duration of Use')
    )
    
    class Meta:
        db_table = 'FU_Antibiotic_28'
        verbose_name = _('Follow-up Antibiotic')
        verbose_name_plural = _('Follow-up Antibiotics')
        unique_together = ['USUBJID', 'EPISODE']
        ordering = ['EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_fua_subj_ep'),
        ]
    
    def __str__(self):
        return f"Antibiotic Episode {self.EPISODE} ({self.ANTIBIONAME}) - {self.USUBJID}"


class FollowUpAntibiotic90(models.Model):
    """
    Antibiotic usage during 90-day follow-up period
    Tracks antibiotic courses between day 28 and day 90
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('FollowUpCase90',
        on_delete=models.CASCADE,
        related_name='antibiotics',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    EPISODE = models.IntegerField(
        default=1,
        verbose_name=_('Episode Number')
    )
    
    ANTIBIONAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Antibiotic Name')
    )
    
    ANTIBIOREASONFOR = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Use')
    )
    
    ANTIBIODUR = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Duration of Use')
    )
    
    class Meta:
        db_table = 'FU_Antibiotic_90'
        verbose_name = _('Follow-up Antibiotic (Day 90)')
        verbose_name_plural = _('Follow-up Antibiotics (Day 90)')
        unique_together = ['USUBJID', 'EPISODE']
        ordering = ['EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_fua90_subj_ep'),
        ]
    
    def __str__(self):
        return f"Antibiotic Episode {self.EPISODE} ({self.ANTIBIONAME}) - {self.USUBJID} (Day 90)"