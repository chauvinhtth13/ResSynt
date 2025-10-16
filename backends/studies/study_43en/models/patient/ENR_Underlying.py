# backends/studies/study_43en/models/UND_UnderlyingCondition.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class UnderlyingCondition(models.Model):
    """
    Patient's underlying conditions/comorbidities
    Each condition is a separate Boolean field
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key (1-to-1 với EnrollmentCase)
    USUBJID = models.OneToOneField('EnrollmentCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='Underlying_Condition',
        verbose_name=_('Patient ID')
    )
    
    # Underlying conditions - mỗi bệnh là 1 trường Boolean
    DIABETES = models.BooleanField(
        default=False,
        verbose_name=_('Diabetes Mellitus')
    )
    
    HEARTFAILURE = models.BooleanField(
        default=False,
        verbose_name=_('Heart Failure')
    )
    
    COPD = models.BooleanField(
        default=False,
        verbose_name=_('COPD')
    )
    
    HEPATITIS = models.BooleanField(
        default=False,
        verbose_name=_('Hepatitis')
    )
    
    CAD = models.BooleanField(
        default=False,
        verbose_name=_('Coronary Artery Disease')
    )
    
    KIDNEYDISEASE = models.BooleanField(
        default=False,
        verbose_name=_('Kidney Disease')
    )
    
    ASTHMA = models.BooleanField(
        default=False,
        verbose_name=_('Asthma')
    )
    
    CIRRHOSIS = models.BooleanField(
        default=False,
        verbose_name=_('Cirrhosis')
    )
    
    HYPERTENSION = models.BooleanField(
        default=False,
        verbose_name=_('Hypertension')
    )
    
    AUTOIMMUNE = models.BooleanField(
        default=False,
        verbose_name=_('Autoimmune Disease')
    )
    
    CANCER = models.BooleanField(
        default=False,
        verbose_name=_('Cancer')
    )
    
    ALCOHOLISM = models.BooleanField(
        default=False,
        verbose_name=_('Alcoholism')
    )
    
    HIV = models.BooleanField(
        default=False,
        verbose_name=_('HIV/AIDS')
    )
    
    ADRENALINSUFFICIENCY = models.BooleanField(
        default=False,
        verbose_name=_('Adrenal Insufficiency')
    )
    
    BEDRIDDEN = models.BooleanField(
        default=False,
        verbose_name=_('Bedridden')
    )
    
    PEPTICULCER = models.BooleanField(
        default=False,
        verbose_name=_('Peptic Ulcer')
    )
    
    COLITIS_IBS = models.BooleanField(
        default=False,
        verbose_name=_('Colitis/IBS')
    )
    
    SENILITY = models.BooleanField(
        default=False,
        verbose_name=_('Senility')
    )
    
    MALNUTRITION_WASTING = models.BooleanField(
        default=False,
        verbose_name=_('Malnutrition/Wasting')
    )
    
    OTHERDISEASE = models.BooleanField(
        default=False,
        verbose_name=_('Other Disease')
    )
    
    OTHERDISEASESPECIFY = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Disease Details')
    )
    
    # Metadata
    ENTRY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Data Entry Person')
    )
    
    ENTEREDTIME = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Entry Time')
    )
    
    class Meta:
        db_table = 'ENR_UnderlyingCondition'
        verbose_name = _('Patient Underlying Condition')
        verbose_name_plural = _('Patient Underlying Conditions')
    
    def __str__(self):
        return f"Underlying Conditions: {self.USUBJID}"
    
    @property
    def has_any_condition(self):
        """Check if patient has any underlying condition"""
        return any([
            self.DIABETES, self.HEARTFAILURE, self.COPD, self.HEPATITIS,
            self.CAD, self.KIDNEYDISEASE, self.ASTHMA, self.CIRRHOSIS,
            self.HYPERTENSION, self.AUTOIMMUNE, self.CANCER, self.ALCOHOLISM,
            self.HIV, self.ADRENALINSUFFICIENCY, self.BEDRIDDEN, self.PEPTICULCER,
            self.COLITIS_IBS, self.SENILITY, self.MALNUTRITION_WASTING, self.OTHERDISEASE
        ])
    
    @property
    def condition_count(self):
        """Count total number of underlying conditions"""
        return sum([
            self.DIABETES, self.HEARTFAILURE, self.COPD, self.HEPATITIS,
            self.CAD, self.KIDNEYDISEASE, self.ASTHMA, self.CIRRHOSIS,
            self.HYPERTENSION, self.AUTOIMMUNE, self.CANCER, self.ALCOHOLISM,
            self.HIV, self.ADRENALINSUFFICIENCY, self.BEDRIDDEN, self.PEPTICULCER,
            self.COLITIS_IBS, self.SENILITY, self.MALNUTRITION_WASTING, self.OTHERDISEASE
        ])