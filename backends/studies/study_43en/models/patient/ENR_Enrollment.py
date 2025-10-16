from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class EnrollmentCase(models.Model):
    """
    Patient enrollment information
    Detailed baseline data for confirmed patients after screening
    """
    
    # Choices definitions using TextChoices
    class SexChoices(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
        OTHER = 'Other', _('Other')
    
    class ResidenceTypeChoices(models.TextChoices):
        URBAN = 'urban', _('Urban')
        SUBURBAN = 'suburban', _('Suburban')
        RURAL = 'rural', _('Rural')
    
    class WorkplaceTypeChoices(models.TextChoices):
        INDOOR = 'indoor', _('Indoor')
        OUTDOOR = 'outdoor', _('Outdoor')
    
    class ThreeStateChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        UNKNOWN = 'unknown', _('Unknown')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with ScreeningCase
    USUBJID = models.OneToOneField('ScreeningCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    # Demographics
    ENRDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Enrollment Date')
    )
    
    RECRUITDEPT = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Recruitment Department')
    )
    
    # Birth information
    DAYOFBIRTH = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Day of Birth')
    )
    
    MONTHOFBIRTH = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Month of Birth')
    )
    
    YEAROFBIRTH = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Year of Birth')
    )
    
    AGEIFDOBUNKNOWN = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Age (if DOB unknown)')
    )
    
    # Basic demographics
    SEX = models.CharField(
        max_length=10,
        choices=SexChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Sex')
    )
    
    ETHNICITY = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Ethnicity')
    )
    
    OCCUPATION = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Occupation')
    )
    
    # Hospital admission info
    FROMOTHERHOSPITAL = models.BooleanField(
        default=False,
        verbose_name=_('Transferred from Other Hospital')
    )
    
    PRIORHOSPIADMISDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Prior Hospital Admission Date')
    )
    
    HEALFACILITYNAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Previous Healthcare Facility Name')
    )
    
    REASONFORADM = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Admission')
    )
    
    # Address information
    WARD = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Ward/Commune')
    )
    
    DISTRICT = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('District')
    )
    
    PROVINCECITY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Province/City')
    )
    
    # Sanitation information
    TOILETNUM = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Number of Toilets')
    )
    
    SHAREDTOILET = models.BooleanField(
        default=False,
        verbose_name=_('Shared Toilet')
    )
    
    # Residence and workplace
    RESIDENCETYPE = models.CharField(
        max_length=20,
        choices=ResidenceTypeChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Residence Type')
    )
    
    WORKPLACETYPE = models.CharField(
        max_length=20,
        choices=WorkplaceTypeChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Workplace Type')
    )
    
    # Risk factors
    HOSP2D6M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Hospitalized ≥2 days in last 6 months')
    )
    
    DIAL3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Dialysis in last 3 months')
    )
    
    CATHETER3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Catheter in last 3 months')
    )
    
    SONDE3M = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Urinary catheter in last 3 months')
    )
    
    HOMEWOUNDCARE = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Home Wound Care')
    )
    
    LONGTERMCAREFACILITY = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Long-term Care Facility')
    )
    
    CORTICOIDPPI = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Corticoid or PPI Use')
    )
    
    # Underlying conditions
    UNDERLYINGCONDS = models.BooleanField(
        default=False,
        verbose_name=_('Has Underlying Conditions')
    )
    
    LISTUNDERLYING = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name=_('List of Underlying Conditions')
    )
    
    OTHERDISEASESPECIFY = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Disease Details')
    )
    
    # Completion info
    COMPLETEDBY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Completed By')
    )
    
    COMPLETEDDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Completion Date')
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
        db_table = 'ENR_Case'
        verbose_name = _('Patient Enrollment')
        verbose_name_plural = _('Patient Enrollments')
        indexes = [
            models.Index(fields=['ENRDATE'], name='idx_enr_date'),
        ]
    
    def __str__(self):
        return f"{self.USUBJID.USUBJID}"
    
    @property
    def SITEID(self):
        """Get SITEID from related ScreeningCase"""
        return self.USUBJID.SITEID
    
    # Property getters for underlying conditions
    @property
    def DIABETES(self):
        return 'DIABETES' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def HEARTFAILURE(self):
        return 'HEARTFAILURE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def COPD(self):
        return 'COPD' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def HEPATITIS(self):
        return 'HEPATITIS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def CAD(self):
        return 'CAD' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def KIDNEYDISEASE(self):
        return 'KIDNEYDISEASE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def ASTHMA(self):
        return 'ASTHMA' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def CIRRHOSIS(self):
        return 'CIRRHOSIS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def HYPERTENSION(self):
        return 'HYPERTENSION' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def AUTOIMMUNE(self):
        return 'AUTOIMMUNE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def CANCER(self):
        return 'CANCER' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def ALCOHOLISM(self):
        return 'ALCOHOLISM' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def HIV(self):
        return 'HIV' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def ADRENALINSUFFICIENCY(self):
        return 'ADRENALINSUFFICIENCY' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def BEDRIDDEN(self):
        return 'BEDRIDDEN' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def PEPTICULCER(self):
        return 'PEPTICULCER' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def COLITIS_IBS(self):
        return 'COLITIS_IBS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def SENILITY(self):
        return 'SENILITY' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def MALNUTRITION_WASTING(self):
        return 'MALNUTRITION_WASTING' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
    @property
    def OTHERDISEASE(self):
        return 'OTHERDISEASE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False