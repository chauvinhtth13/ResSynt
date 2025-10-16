from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ContactEndCaseCRF(models.Model):
    """Contact end-of-study case report form"""
    
    # Choices definitions using TextChoices
    class WithdrawReasonChoices(models.TextChoices):
        WITHDRAW = 'withdraw', _('Voluntary Withdrawal')
        FORCED = 'forced', _('Forced Withdrawal')
        NA = 'na', _('Not Applicable')
    
    class YesNoNAChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        NA = 'na', _('Not Applicable')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key
    USUBJID = models.OneToOneField(
        'EnrollmentContact',
        on_delete=models.CASCADE,
        to_field='USUBJID',
        db_column='USUBJID',
        primary_key=True,
        verbose_name=_('Contact')
    )
    
    # End dates
    ENDDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('End Date Recorded')
    )
    
    ENDFORMDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Study End Date')
    )
    
    # Visit completion
    VICOMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V1 Completed (Enrollment)')
    )
    
    V2COMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V2 Completed (Day 28±3)')
    )
    
    V3COMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V3 Completed (Day 90±3)')
    )
    
    # Withdrawal
    WITHDRAWREASON = models.CharField(
        max_length=10,
        choices=WithdrawReasonChoices.choices,
        default=WithdrawReasonChoices.NA,
        verbose_name=_('Withdrawal Reason')
    )
    
    # Incomplete reasons
    INCOMPLETE = models.CharField(
        max_length=3,
        choices=YesNoNAChoices.choices,
        default=YesNoNAChoices.NA,
        verbose_name=_('Unable to Complete Study')
    )
    
    INCOMPLETEDEATH = models.BooleanField(
        default=False,
        verbose_name=_('Participant Death')
    )
    
    INCOMPLETEMOVED = models.BooleanField(
        default=False,
        verbose_name=_('Participant Moved/Relocated')
    )
    
    INCOMPLETEOTHER = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Reason, Specify')
    )
    
    # Lost to follow-up
    LOSTTOFOLLOWUP = models.CharField(
        max_length=3,
        choices=YesNoNAChoices.choices,
        default=YesNoNAChoices.NA,
        verbose_name=_('Lost to Follow-up')
    )
    
    # Metadata
    CREATEDAT = models.DateTimeField(auto_now_add=True)
    UPDATEDAT = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Contact_End_Case_CRF'
        verbose_name = _('Contact End Case CRF')
        verbose_name_plural = _('Contact End Case CRFs')

    def __str__(self):
        return f"End Case - {self.USUBJID.USUBJID}"