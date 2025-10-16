from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class PriorAntibiotic(models.Model):
    """
    Prior antibiotic usage before study enrollment
    Tracks antibiotics used before patient entered the study
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
        related_name='prior_antibiotics',
        verbose_name=_('Patient ID')
    )
    
    PRIORANTIBIONAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Prior Antibiotic Name')
    )
    
    PRIORANTIBIODOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Prior Antibiotic Dosage')
    )
    
    PRIORANTIBIOSTARTDTC = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Prior Antibiotic Start Date')
    )
    
    PRIORANTIBIOENDDTC = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Prior Antibiotic End Date')
    )

    class Meta:
        db_table = 'CLI_Prior_Antibiotic'
        verbose_name = _('Prior Antibiotic')
        verbose_name_plural = _('Prior Antibiotics')
        ordering = ['PRIORANTIBIOSTARTDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'PRIORANTIBIOSTARTDTC'], name='idx_pa_subj_start'),
        ]

    def __str__(self):
        return f"{self.PRIORANTIBIONAME} - {self.PRIORANTIBIODOSAGE}"


class InitialAntibiotic(models.Model):
    """
    Initial antibiotic treatment at study enrollment
    First-line antibiotics given when patient entered study
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('ClinicalCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='initial_antibiotics',
        verbose_name=_('Patient ID')
    )
    
    INITIALANTIBIONAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Initial Antibiotic Name')
    )
    
    INITIALANTIBIODOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Initial Antibiotic Dosage')
    )
    
    INITIALANTIBIOSTARTDTC = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Initial Antibiotic Start Date')
    )
    
    INITIALANTIBIOENDDTC = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Initial Antibiotic End Date')
    )

    class Meta:
        db_table = 'CLI_Initial_Antibiotic'
        verbose_name = _('Initial Antibiotic')
        verbose_name_plural = _('Initial Antibiotics')
        ordering = ['INITIALANTIBIOSTARTDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'INITIALANTIBIOSTARTDTC'], name='idx_ia_subj_start'),
        ]

    def __str__(self):
        return f"{self.INITIALANTIBIONAME} - {self.INITIALANTIBIODOSAGE}"


class MainAntibiotic(models.Model):
    """
    Main antibiotic treatment during hospitalization
    Primary antibiotics used for definitive treatment
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('ClinicalCase',
        to_field='USUBJID',
        on_delete=models.CASCADE,
        related_name='main_antibiotics',
        verbose_name=_('Patient ID'),
        db_column='USUBJID'
    )
    
    MAINANTIBIONAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Main Antibiotic Name')
    )
    
    MAINANTIBIODOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Main Antibiotic Dosage')
    )
    
    MAINANTIBIOSTARTDTC = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Main Antibiotic Start Date')
    )
    
    MAINANTIBIOENDDTC = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Main Antibiotic End Date')
    )

    class Meta:
        db_table = 'CLI_Main_Antibiotic'
        verbose_name = _('Main Antibiotic')
        verbose_name_plural = _('Main Antibiotics')
        ordering = ['MAINANTIBIOSTARTDTC']
        indexes = [
            models.Index(fields=['USUBJID', 'MAINANTIBIOSTARTDTC'], name='idx_ma_subj_start'),
        ]

    def __str__(self):
        return f"{self.MAINANTIBIONAME} - {self.MAINANTIBIODOSAGE}"