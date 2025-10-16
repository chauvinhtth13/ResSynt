from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class EnrollmentContact(models.Model):
    """
    Contact enrollment information
    Detailed baseline data for confirmed contacts
    
    NOTE: Underlying conditions are now in ContactUnderlyingCondition model.
    Access via: enrollment_contact.underlying_condition.DIABETES
    """
    
    # Choices definitions using TextChoices
    class SexChoices(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
        OTHER = 'Other', _('Other')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with ScreeningContact
    USUBJID = models.OneToOneField(
        'ScreeningContact',
        on_delete=models.CASCADE,
        to_field='USUBJID',
        db_column='USUBJID',
        primary_key=True,
        verbose_name=_('Contact ID')
    )
    
    # Demographics
    ENRDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Enrollment Date')
    )
    
    RELATIONSHIP = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Relationship to Patient')
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
    
    SPECIFYIFOTHERETHNI = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Other Ethnicity Details')
    )
    
    OCCUPATION = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Occupation')
    )
    
    # Risk factors / Healthcare exposure
    HOSP2D6M = models.BooleanField(
        default=False,
        verbose_name=_('Hospitalized ≥2 days in last 6 months')
    )
    
    DIAL3M = models.BooleanField(
        default=False,
        verbose_name=_('Dialysis in last 3 months')
    )
    
    CATHETER3M = models.BooleanField(
        default=False,
        verbose_name=_('Catheter in last 3 months')
    )
    
    SONDE3M = models.BooleanField(
        default=False,
        verbose_name=_('Urinary catheter in last 3 months')
    )
    
    HOMEWOUNDCARE = models.BooleanField(
        default=False,
        verbose_name=_('Home wound care')
    )
    
    LONGTERMCAREFACILITY = models.BooleanField(
        default=False,
        verbose_name=_('Long-term care facility')
    )
    
    CORTICOIDPPI = models.BooleanField(
        default=False,
        verbose_name=_('Corticoid or PPI use')
    )
    
    # Underlying conditions - simplified boolean flag
    UNDERLYINGCONDS = models.BooleanField(
        default=False,
        verbose_name=_('Has Underlying Conditions')
    )
    
    # Medication history
    MEDHISDRUG = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Medication History')
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
        db_table = 'Contact_ENR_Case'
        verbose_name = _('Contact Enrollment')
        verbose_name_plural = _('Contact Enrollments')
        indexes = [
            models.Index(fields=['ENRDATE'], name='idx_ec_enrdate'),
        ]
    
    def __str__(self):
        return f"{self.USUBJID.USUBJID}"