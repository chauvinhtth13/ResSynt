from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class EndCaseCRF(AuditFieldsMixin):
    """
    End of study case report form
    Final study completion status and visit tracking
    
    Optimizations:
    - Added AuditFieldsMixin for compliance and version control
    - Enhanced validation for dates and visit dependencies
    - Cached properties for computed values
    - Better indexes for common queries
    - Query helper methods for reporting
    
    Inherits from AuditFieldsMixin:
    - version: Optimistic locking version control
    - last_modified_by_id: User ID who last modified
    - last_modified_by_username: Username backup for audit
    - last_modified_at: Timestamp of last modification
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
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
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CASE',
        on_delete=models.CASCADE,
        to_field='USUBJID',
        db_column='USUBJID',
        primary_key=True,
        related_name='end_case',
        verbose_name=_('Patient ID')
    )
    
    # ==========================================
    # END DATES
    # ==========================================
    ENDDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('End Date Recorded'),
        help_text=_('Date when patient ended study participation')
    )
    
    ENDFORMDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Study End Date'),
        help_text=_('Date when end case form was completed')
    )
    
    # ==========================================
    # VISIT COMPLETION STATUS
    # ==========================================
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
    
    # ==========================================
    # WITHDRAWAL INFORMATION
    # ==========================================
    WITHDRAWREASON = models.CharField(
        max_length=10,
        choices=WithdrawReasonChoices.choices,
        default=WithdrawReasonChoices.NA,
        db_index=True,
        verbose_name=_('Withdrawal Reason')
    )
    
    WITHDRAWDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Withdrawal Date'),
        help_text=_('Date when patient withdrew from study')
    )
    
    WITHDRAWDETAILS = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Withdrawal Details'),
        help_text=_('Additional information about withdrawal')
    )
    
    # ==========================================
    # INCOMPLETE STUDY REASONS
    # ==========================================
    INCOMPLETE = models.CharField(
        max_length=3,
        choices=IncompleteChoices.choices,
        default=IncompleteChoices.NA,
        db_index=True,
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
    
    # ==========================================
    # LOST TO FOLLOW-UP
    # ==========================================
    LOSTTOFOLLOWUP = models.CharField(
        max_length=3,
        choices=LostToFollowUpChoices.choices,
        default=LostToFollowUpChoices.NA,
        db_index=True,
        verbose_name=_('Lost to Follow-up')
    )
    
    LOSTTOFOLLOWUPDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Lost to Follow-up Date'),
        help_text=_('Date when patient was determined lost to follow-up')
    )
    
    # ==========================================
    # STUDY COMPLETION STATUS
    # ==========================================
    STUDYCOMPLETED = models.BooleanField(
        default=False,
        verbose_name=_('Study Fully Completed'),
        help_text=_('All required visits completed successfully')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'End_Case_CRF'
        verbose_name = _('End Case CRF')
        verbose_name_plural = _('End Case CRFs')
        ordering = ['-ENDDATE']
        indexes = [
            models.Index(fields=['ENDDATE'], name='idx_ec_enddate'),
            models.Index(fields=['WITHDRAWREASON'], name='idx_ec_withdraw'),
            models.Index(fields=['INCOMPLETE'], name='idx_ec_incomplete'),
            models.Index(fields=['LOSTTOFOLLOWUP'], name='idx_ec_ltfu'),
            models.Index(fields=['STUDYCOMPLETED', 'ENDDATE'], name='idx_ec_comp_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_ec_modified'),
        ]
        constraints = [
            # If withdrawn, must have withdrawal date
            models.CheckConstraint(
                condition=(
                    models.Q(WITHDRAWREASON='na') |
                    models.Q(WITHDRAWDATE__isnull=False)
                ),
                name='ec_withdraw_date_required'
            ),
            # If incomplete due to other reason, must specify
            models.CheckConstraint(
                condition=(
                    ~models.Q(INCOMPLETE='yes') |
                    models.Q(INCOMPLETEDEATH=True) |
                    models.Q(INCOMPLETEMOVED=True) |
                    models.Q(INCOMPLETEOTHER__isnull=False)
                ),
                name='ec_incomplete_reason_required'
            ),
            # If lost to follow-up YES, must have date
            models.CheckConstraint(
                condition=(
                    ~models.Q(LOSTTOFOLLOWUP='yes') |
                    models.Q(LOSTTOFOLLOWUPDATE__isnull=False)
                ),
                name='ec_ltfu_date_required'
            ),
        ]
    
    def __str__(self):
        return f"End Case - {self.USUBJID.USUBJID if hasattr(self.USUBJID, 'USUBJID') else self.USUBJID_id}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def total_visits_completed(self):
        """Count total number of completed visits"""
        return sum([
            self.VICOMPLETED,
            self.V2COMPLETED,
            self.V3COMPLETED,
            self.V4COMPLETED
        ])
    
    @cached_property
    def completion_rate(self):
        """Calculate visit completion rate (0-100%)"""
        return (self.total_visits_completed / 4) * 100
    
    @cached_property
    def is_withdrawn(self):
        """Check if patient withdrew from study"""
        return self.WITHDRAWREASON in [
            self.WithdrawReasonChoices.WITHDRAW,
            self.WithdrawReasonChoices.FORCED
        ]
    
    @cached_property
    def is_lost_to_followup(self):
        """Check if patient is lost to follow-up"""
        return self.LOSTTOFOLLOWUP == self.LostToFollowUpChoices.YES
    
    @cached_property
    def is_incomplete(self):
        """Check if study is incomplete"""
        return self.INCOMPLETE == self.IncompleteChoices.YES
    
    @cached_property
    def study_duration_days(self):
        """Calculate study duration from enrollment to end"""
        if self.ENDDATE and self.USUBJID and self.USUBJID.ENRDATE:
            delta = self.ENDDATE - self.USUBJID.ENRDATE
            return delta.days
        return None
    
    @cached_property
    def incomplete_reason_list(self):
        """Get list of reasons for incomplete study"""
        reasons = []
        if self.INCOMPLETEDEATH:
            reasons.append(_('Participant Death'))
        if self.INCOMPLETEMOVED:
            reasons.append(_('Participant Moved/Relocated'))
        if self.INCOMPLETEOTHER:
            reasons.append(f"{_('Other')}: {self.INCOMPLETEOTHER}")
        return reasons
    
    @cached_property
    def visit_completion_summary(self):
        """Get summary of visit completions"""
        return {
            'V1': self.VICOMPLETED,
            'V2': self.V2COMPLETED,
            'V3': self.V3COMPLETED,
            'V4': self.V4COMPLETED,
            'total': self.total_visits_completed,
            'rate': self.completion_rate
        }
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    @property
    def all_visits_completed(self):
        """Check if all visits were completed"""
        return all([
            self.VICOMPLETED,
            self.V2COMPLETED,
            self.V3COMPLETED,
            self.V4COMPLETED
        ])
    
    @property
    def has_early_termination(self):
        """Check if study ended early"""
        return (self.is_withdrawn or 
                self.is_lost_to_followup or 
                self.is_incomplete)
    
    @property
    def termination_reason(self):
        """Get primary reason for study termination"""
        if self.is_withdrawn:
            return self.get_WITHDRAWREASON_display()
        elif self.is_lost_to_followup:
            return _('Lost to Follow-up')
        elif self.is_incomplete:
            reasons = self.incomplete_reason_list
            return ', '.join(reasons) if reasons else _('Incomplete - Reason not specified')
        elif self.all_visits_completed:
            return _('Study Completed Successfully')
        else:
            return _('In Progress')
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation with comprehensive checks"""
        errors = {}
        
        # Validate end dates - simple logic only
        if self.ENDDATE:
            try:
                if self.USUBJID and hasattr(self.USUBJID, 'ENRDATE') and self.USUBJID.ENRDATE:
                    if self.ENDDATE < self.USUBJID.ENRDATE:
                        errors['ENDDATE'] = _('End date cannot be before enrollment date')
            except Exception:
                pass
        
        # Validate withdrawal information
        if self.is_withdrawn:
            if not self.WITHDRAWDATE:
                errors['WITHDRAWDATE'] = _('Withdrawal date is required when patient withdrew')
        
        # Validate incomplete information
        if self.INCOMPLETE == self.IncompleteChoices.YES:
            if not any([self.INCOMPLETEDEATH, self.INCOMPLETEMOVED, self.INCOMPLETEOTHER]):
                errors['INCOMPLETE'] = _(
                    'At least one reason must be provided when study is marked incomplete'
                )
            
            # If other reason selected, must specify
            if not self.INCOMPLETEDEATH and not self.INCOMPLETEMOVED:
                if not self.INCOMPLETEOTHER or not self.INCOMPLETEOTHER.strip():
                    errors['INCOMPLETEOTHER'] = _(
                        'Please specify other reason when study is incomplete'
                    )
        
        # Validate lost to follow-up
        if self.LOSTTOFOLLOWUP == self.LostToFollowUpChoices.YES:
            if not self.LOSTTOFOLLOWUPDATE:
                errors['LOSTTOFOLLOWUPDATE'] = _(
                    'Lost to follow-up date is required'
                )
        
        # Validate study completion status consistency
        if self.STUDYCOMPLETED:
            if not self.all_visits_completed:
                errors['STUDYCOMPLETED'] = _(
                    'Cannot mark study as completed when not all visits are completed'
                )
            if self.has_early_termination:
                errors['STUDYCOMPLETED'] = _(
                    'Cannot mark study as completed when patient withdrew, was lost to follow-up, or study is incomplete'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with auto-calculations and cache management"""
        # Clear cached properties
        self._clear_cache()
        
        # Strip whitespace from text fields
        if self.INCOMPLETEOTHER:
            self.INCOMPLETEOTHER = self.INCOMPLETEOTHER.strip()
        if self.WITHDRAWDETAILS:
            self.WITHDRAWDETAILS = self.WITHDRAWDETAILS.strip()
        
        # Auto-set study completion flag
        self.STUDYCOMPLETED = (
            self.all_visits_completed and 
            not self.has_early_termination
        )
        
        # Auto-set end date if not provided but study completed
        if self.STUDYCOMPLETED and not self.ENDDATE:
            self.ENDDATE = date.today()
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_total_visits_completed', '_completion_rate',
            '_is_withdrawn', '_is_lost_to_followup', '_is_incomplete',
            '_study_duration_days', '_incomplete_reason_list',
            '_visit_completion_summary'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_completed_studies(cls):
        """Get all cases that completed the study"""
        return cls.objects.filter(
            STUDYCOMPLETED=True
        ).select_related('USUBJID')
    
    @classmethod
    def get_withdrawn_cases(cls):
        """Get all cases that withdrew from study"""
        return cls.objects.exclude(
            WITHDRAWREASON=cls.WithdrawReasonChoices.NA
        ).select_related('USUBJID').order_by('-WITHDRAWDATE')
    
    @classmethod
    def get_lost_to_followup_cases(cls):
        """Get all cases lost to follow-up"""
        return cls.objects.filter(
            LOSTTOFOLLOWUP=cls.LostToFollowUpChoices.YES
        ).select_related('USUBJID').order_by('-LOSTTOFOLLOWUPDATE')
    
    @classmethod
    def get_incomplete_cases(cls):
        """Get all incomplete study cases"""
        return cls.objects.filter(
            INCOMPLETE=cls.IncompleteChoices.YES
        ).select_related('USUBJID')
    
    @classmethod
    def get_early_termination_cases(cls):
        """Get all cases with early termination"""
        from django.db.models import Q
        return cls.objects.filter(
            Q(LOSTTOFOLLOWUP=cls.LostToFollowUpChoices.YES) |
            Q(INCOMPLETE=cls.IncompleteChoices.YES) |
            ~Q(WITHDRAWREASON=cls.WithdrawReasonChoices.NA)
        ).select_related('USUBJID')
    
    @classmethod
    def get_completion_statistics(cls):
        """
        Get study completion statistics
        
        Returns:
            dict: Statistics on study completion rates
        """
        total_cases = cls.objects.count()
        
        stats = {
            'total_cases': total_cases,
            'completed': cls.objects.filter(STUDYCOMPLETED=True).count(),
            'withdrawn': cls.objects.exclude(
                WITHDRAWREASON=cls.WithdrawReasonChoices.NA
            ).count(),
            'lost_to_followup': cls.objects.filter(
                LOSTTOFOLLOWUP=cls.LostToFollowUpChoices.YES
            ).count(),
            'incomplete': cls.objects.filter(
                INCOMPLETE=cls.IncompleteChoices.YES
            ).count(),
            'visit_completion_rates': {
                'V1': cls.objects.filter(VICOMPLETED=True).count(),
                'V2': cls.objects.filter(V2COMPLETED=True).count(),
                'V3': cls.objects.filter(V3COMPLETED=True).count(),
                'V4': cls.objects.filter(V4COMPLETED=True).count(),
            }
        }
        
        # Calculate percentages
        if total_cases > 0:
            stats['completion_rate'] = (stats['completed'] / total_cases) * 100
            stats['withdrawal_rate'] = (stats['withdrawn'] / total_cases) * 100
            stats['ltfu_rate'] = (stats['lost_to_followup'] / total_cases) * 100
            
            for visit, count in stats['visit_completion_rates'].items():
                stats['visit_completion_rates'][visit] = {
                    'count': count,
                    'percentage': (count / total_cases) * 100
                }
        
        return stats
    
    @classmethod
    def get_cases_by_completion_rate(cls, min_rate=0, max_rate=100):
        """
        Get cases within a specific completion rate range
        
        Args:
            min_rate: Minimum completion rate (0-100)
            max_rate: Maximum completion rate (0-100)
        
        Returns:
            List of EndCaseCRF instances
        """
        cases = []
        for case in cls.objects.select_related('USUBJID'):
            rate = case.completion_rate
            if min_rate <= rate <= max_rate:
                cases.append(case)
        return cases
    
    @classmethod
    def get_duration_analysis(cls):
        """
        Analyze study duration for completed cases
        
        Returns:
            dict: Duration statistics
        """
        completed_cases = cls.get_completed_studies()
        durations = [
            case.study_duration_days 
            for case in completed_cases 
            if case.study_duration_days is not None
        ]
        
        if durations:
            return {
                'count': len(durations),
                'mean': sum(durations) / len(durations),
                'min': min(durations),
                'max': max(durations),
                'median': sorted(durations)[len(durations) // 2]
            }
        
        return None


# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def generate_completion_report(site_id=None, start_date=None, end_date=None):
    """
    Generate comprehensive completion report
    
    Args:
        site_id: Filter by site
        start_date: Start date for filtering
        end_date: End date for filtering
    
    Returns:
        dict: Comprehensive completion report
    """
    qs = EndCaseCRF.objects.all()
    
    if site_id:
        qs = qs.filter(USUBJID__USUBJID__SITEID=site_id)
    
    if start_date:
        qs = qs.filter(ENDDATE__gte=start_date)
    
    if end_date:
        qs = qs.filter(ENDDATE__lte=end_date)
    
    report = {
        'period': {
            'start': start_date,
            'end': end_date,
            'site': site_id
        },
        'overall': EndCaseCRF.get_completion_statistics(),
        'duration_analysis': EndCaseCRF.get_duration_analysis(),
        'withdrawal_reasons': {},
        'incomplete_reasons': {},
    }
    
    # Withdrawal reasons breakdown
    for reason in EndCaseCRF.WithdrawReasonChoices.values:
        count = qs.filter(WITHDRAWREASON=reason).count()
        if count > 0:
            report['withdrawal_reasons'][reason] = count
    
    # Incomplete reasons breakdown
    report['incomplete_reasons'] = {
        'death': qs.filter(INCOMPLETEDEATH=True).count(),
        'moved': qs.filter(INCOMPLETEMOVED=True).count(),
        'other': qs.filter(INCOMPLETEOTHER__isnull=False).count(),
    }
    
    return report