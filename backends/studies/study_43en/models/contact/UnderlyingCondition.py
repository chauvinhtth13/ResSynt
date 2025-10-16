from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ContactUnderlyingCondition(models.Model):
    """
    Contact underlying conditions - separated from EnrollmentContact
    OneToOne relationship with EnrollmentContact
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with EnrollmentContact
    USUBJID = models.OneToOneField('EnrollmentContact',
        on_delete=models.CASCADE,
        to_field='USUBJID',
        db_column='USUBJID',
        primary_key=True,
        related_name='underlying_condition',
        verbose_name=_('Contact')
    )
    
    # Cardiovascular conditions
    HEARTFAILURE = models.BooleanField(
        default=False,
        verbose_name=_('Heart Failure')
    )
    
    CAD = models.BooleanField(
        default=False,
        verbose_name=_('Coronary Artery Disease')
    )
    
    HYPERTENSION = models.BooleanField(
        default=False,
        verbose_name=_('Hypertension')
    )
    
    # Metabolic conditions
    DIABETES = models.BooleanField(
        default=False,
        verbose_name=_('Diabetes')
    )
    
    # Respiratory conditions
    COPD = models.BooleanField(
        default=False,
        verbose_name=_('COPD')
    )
    
    ASTHMA = models.BooleanField(
        default=False,
        verbose_name=_('Asthma')
    )
    
    # Liver conditions
    HEPATITIS = models.BooleanField(
        default=False,
        verbose_name=_('Hepatitis')
    )
    
    CIRRHOSIS = models.BooleanField(
        default=False,
        verbose_name=_('Cirrhosis')
    )
    
    # Kidney conditions
    KIDNEYDISEASE = models.BooleanField(
        default=False,
        verbose_name=_('Kidney Disease')
    )
    
    # Immune system
    AUTOIMMUNE = models.BooleanField(
        default=False,
        verbose_name=_('Autoimmune Disease')
    )
    
    HIV = models.BooleanField(
        default=False,
        verbose_name=_('HIV')
    )
    
    # Cancer
    CANCER = models.BooleanField(
        default=False,
        verbose_name=_('Cancer')
    )
    
    # Endocrine
    ADRENALINSUFFICIENCY = models.BooleanField(
        default=False,
        verbose_name=_('Adrenal Insufficiency')
    )
    
    # Lifestyle/Behavioral
    ALCOHOLISM = models.BooleanField(
        default=False,
        verbose_name=_('Alcoholism')
    )
    
    BEDRIDDEN = models.BooleanField(
        default=False,
        verbose_name=_('Bedridden')
    )
    
    # Gastrointestinal
    PEPTICULCER = models.BooleanField(
        default=False,
        verbose_name=_('Peptic Ulcer')
    )
    
    COLITIS_IBS = models.BooleanField(
        default=False,
        verbose_name=_('Colitis/IBS')
    )
    
    # Geriatric
    SENILITY = models.BooleanField(
        default=False,
        verbose_name=_('Senility')
    )
    
    MALNUTRITION_WASTING = models.BooleanField(
        default=False,
        verbose_name=_('Malnutrition/Wasting')
    )
    
    # Other
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
    ENTRY = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Entry Number')
    )
    
    ENTEREDTIME = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Entry Time')
    )
    
    class Meta:
        db_table = 'Contact_Underlying_Conditions'
        verbose_name = _('Contact Underlying Condition')
        verbose_name_plural = _('Contact Underlying Conditions')
    
    def __str__(self):
        return f"Underlying Conditions - {self.USUBJID.USUBJID}"
    
    def get_condition_list(self):
        """Return list of active conditions"""
        conditions = []
        condition_fields = [
            'HEARTFAILURE', 'DIABETES', 'COPD', 'HEPATITIS', 'CAD',
            'KIDNEYDISEASE', 'ASTHMA', 'CIRRHOSIS', 'HYPERTENSION',
            'AUTOIMMUNE', 'CANCER', 'ALCOHOLISM', 'HIV',
            'ADRENALINSUFFICIENCY', 'BEDRIDDEN', 'PEPTICULCER',
            'COLITIS_IBS', 'SENILITY', 'MALNUTRITION_WASTING', 'OTHERDISEASE'
        ]
        for field in condition_fields:
            if getattr(self, field, False):
                conditions.append(field)
        return conditions