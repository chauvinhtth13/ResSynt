from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class AEHospEvent(models.Model):
    """
    Adverse events during hospitalization
    Tracks complications and adverse events occurring during hospital stay
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey(
        'ClinicalCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='AEHospEvent',
        verbose_name=_('Patient ID')
    )
    
    AENAME = models.CharField(
        max_length=255,
        verbose_name=_('Adverse Event Name')
    )
    
    AEDETAILS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Adverse Event Details')
    )
    
    AEDTC = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Assessment Date')
    )

    class Meta:
        db_table = 'CLI_Aehosp_Event'
        verbose_name = _('Adverse Event During Hospitalization')
        verbose_name_plural = _('Adverse Events During Hospitalization')
        ordering = ['AEDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'AEDTC'], name='idx_ae_subj_date'),
        ]

    def __str__(self):
        return f"{self.AENAME} - {self.USUBJID_id}"