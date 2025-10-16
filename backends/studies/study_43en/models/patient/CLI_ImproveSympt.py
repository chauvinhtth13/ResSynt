from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ImproveSympt(models.Model):
    """
    Symptom improvement tracking
    Documents improvement in initial symptoms
    """
    
    # Choices definitions using TextChoices
    class YesNoChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('ClinicalCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='ImproveSympt',
        verbose_name=_('Patient ID')
    )
    
    IMPROVE_SYMPTS = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        verbose_name=_('Initial Symptoms Improved?')
    )
    
    SYMPTS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Symptoms')
    )
    
    IMPROVE_CONDITIONS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Improvement Conditions')
    )
    
    SYMPTSDTC = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Assessment Date')
    )

    class Meta:
        db_table = 'CLI_Improve_Sympt'
        verbose_name = _('Symptom Improvement')
        verbose_name_plural = _('Symptom Improvements')
        ordering = ['SYMPTSDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'SYMPTSDTC'], name='idx_is_subj_date'),
        ]

    def __str__(self):
        return f"{self.get_IMPROVE_SYMPTS_display()} - {self.USUBJID_id}"