from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class EndCaseCRF(models.Model):
    """
    End of study case report form
    Final study completion status and visit tracking
    """
    
    # Choices definitions using TextChoices
    class WithdrawReasonChoices(models.TextChoices):
        WITHDRAW = 'withdraw', _('Voluntary Withdrawal')
        FORCED = 'forced', _('Forced Withdrawal')
        NA = 'na', _('Not Applicable')
    
    class IncompleteChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        NA = 'na', _('Not Applicable')
    
    class LostToFollowUpChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        NA = 'na', _('Not Applicable')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with EnrollmentCase
    USUBJID = models.OneToOneField('EnrollmentCase',
        on_delete=models.CASCADE,
        to_field='USUBJID',
        db_column='USUBJID',
        primary_key=True,
        verbose_name=_('Patient ID')
    )
    
    # End dates
    ENDDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('End Date Recorded')
    )
    
    ENDFORMDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Study End Date')
    )
    
    # Visit completion status
    VICOMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V1 Completed (Enrollment)')
    )
    
    V2COMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V2 Completed (Day 10±3)')
    )
    
    V3COMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V3 Completed (Day 28±3)')
    )
    
    V4COMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('V4 Completed (Day 90±3)')
    )
    
    # Withdrawal reason
    WITHDRAWREASON = models.CharField(
        max_length=10,
        choices=WithdrawReasonChoices.choices,
        default=WithdrawReasonChoices.NA,
        verbose_name=_('Withdrawal Reason')
    )
    
    # Incomplete reasons
    INCOMPLETE = models.CharField(
        max_length=3,
        choices=IncompleteChoices.choices,
        default=IncompleteChoices.NA,
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
        choices=LostToFollowUpChoices.choices,
        default=LostToFollowUpChoices.NA,
        verbose_name=_('Lost to Follow-up')
    )
    
    # Metadata
    CREATEDAT = models.DateTimeField(auto_now_add=True)
    UPDATEDAT = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'End_Case_CRF'
        verbose_name = _('End Case CRF')
        verbose_name_plural = _('End Case CRFs')
        indexes = [
            models.Index(fields=['ENDDATE'], name='idx_ec_enddate'),
            models.Index(fields=['WITHDRAWREASON'], name='idx_ec_withdraw'),
        ]
    
    def __str__(self):
        return f"End Case - {self.USUBJID.USUBJID}"