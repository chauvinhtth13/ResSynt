from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class HospiProcess(models.Model):
    """
    Hospitalization process tracking
    Documents patient transfers between departments
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('ClinicalCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='hospiprocesses',
        verbose_name=_('Patient ID')
    )
    
    DEPTNAME = models.CharField(
        max_length=255,
        verbose_name=_('Department Name')
    )
    
    STARTDTC = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Start Date')
    )
    
    ENDDTC = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('End Date')
    )
    
    TRANSFER_REASON = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Transfer Reason')
    )

    class Meta:
        db_table = 'CLI_Hospi_Process'
        verbose_name = _('Hospitalization Process')
        verbose_name_plural = _('Hospitalization Processes')
        ordering = ['STARTDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'STARTDTC'], name='idx_hp_subj_start'),
        ]

    def __str__(self):
        return f"{self.DEPTNAME} - {self.USUBJID_id}"