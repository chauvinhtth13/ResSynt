from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class Rehospitalization(models.Model):
    """
    Rehospitalization records during follow-up
    Tracks multiple rehospitalization episodes
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('FollowUpCase',
        on_delete=models.CASCADE,
        related_name='rehospitalization',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    EPISODE = models.IntegerField(
        default=1,
        verbose_name=_('Episode Number')
    )
    
    REHOSPDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Rehospitalization Date')
    )
    
    REHOSPREASONFOR = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Rehospitalization')
    )
    
    REHOSPLOCATION = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Rehospitalization Location')
    )
    
    REHOSPSTAYDUR = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Hospital Stay Duration')
    )
    
    class Meta:
        db_table = 'FU_Rehospitalization_28'
        verbose_name = _('Rehospitalization')
        verbose_name_plural = _('Rehospitalizations')
        unique_together = ['USUBJID', 'EPISODE']
        ordering = ['EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_rh_subj_ep'),
            models.Index(fields=['REHOSPDATE'], name='idx_rh_date'),
        ]
    
    def __str__(self):
        return f"Rehospitalization Episode {self.EPISODE} - {self.USUBJID}"


class Rehospitalization90(models.Model):
    """
    Rehospitalization records during 90-day follow-up
    Tracks multiple rehospitalization episodes after initial discharge
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('FollowUpCase90',
        on_delete=models.CASCADE,
        related_name='rehospitalization',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    EPISODE = models.IntegerField(
        default=1,
        verbose_name=_('Episode Number')
    )
    
    REHOSPDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Rehospitalization Date')
    )
    
    REHOSPREASONFOR = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Rehospitalization')
    )
    
    REHOSPLOCATION = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Rehospitalization Location')
    )
    
    REHOSPSTAYDUR = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Hospital Stay Duration')
    )
    
    class Meta:
        db_table = 'FU_Rehospitalization_90'
        verbose_name = _('Rehospitalization (Day 90)')
        verbose_name_plural = _('Rehospitalizations (Day 90)')
        unique_together = ['USUBJID', 'EPISODE']
        ordering = ['EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_rh90_subj_ep'),
            models.Index(fields=['REHOSPDATE'], name='idx_rh90_date'),
        ]
    
    def __str__(self):
        return f"Rehospitalization Episode {self.EPISODE} - {self.USUBJID} (Day 90)"