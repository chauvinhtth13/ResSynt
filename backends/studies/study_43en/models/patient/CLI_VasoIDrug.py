from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class VasoIDrug(models.Model):
    """
    Vasoactive and inotropic drug usage
    Tracks vasopressor and inotrope administration
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('ClinicalCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='vaso_drugs',
        verbose_name=_('Patient ID')
    )
    
    VASOIDRUGNAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Vasoactive Drug Name')
    )
    
    VASOIDRUGDOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Vasoactive Drug Dosage')
    )
    
    VASOIDRUGSTARTDTC = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Vasoactive Drug Start Date')
    )
    
    VASOIDRUGENDDTC = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Vasoactive Drug End Date')
    )

    class Meta:
        db_table = 'CLI_Vasoi_Drug'
        verbose_name = _('Vasoactive Drug')
        verbose_name_plural = _('Vasoactive Drugs')
        ordering = ['VASOIDRUGSTARTDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'VASOIDRUGSTARTDTC'], name='idx_vd_subj_start'),
        ]

    def __str__(self):
        return f"{self.VASOIDRUGNAME} - {self.VASOIDRUGDOSAGE}"