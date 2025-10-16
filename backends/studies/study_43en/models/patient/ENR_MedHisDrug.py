from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class MedHisDrug(models.Model):
    """Patient medication history - formset for multiple drugs"""
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    USUBJID = models.ForeignKey('EnrollmentCase',
        on_delete=models.CASCADE,
        related_name='medhisdrug_set',
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient')
    )
    
    SEQUENCE = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Sequence Number')
    )
    
    DRUGNAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Drug Name')
    )
    
    DOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Dosage')
    )
    
    USAGETIME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Usage Duration')
    )
    
    USAGEREASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Usage Reason')
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
        db_table = 'ENR_History_Drug'
        verbose_name = _('Drug History')
        verbose_name_plural = _('Drug Histories')
        ordering = ['SEQUENCE']

    def __str__(self):
        return f"{self.USUBJID} - {self.DRUGNAME}"
    
    @property
    def SITEID(self):
        """Get SITEID from related EnrollmentCase"""
        return self.USUBJID.SITEID if self.USUBJID else None