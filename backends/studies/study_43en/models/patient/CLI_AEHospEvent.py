from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class AEHospEvent(AuditFieldsMixin):
    """
    Adverse events during hospitalization
    Tracks complications and adverse events occurring during hospital stay
    
    Optimizations:
    - Added AuditFieldsMixin
    - Auto-incrementing SEQUENCE
    - Validation for dates and event details
    - Bulk operations support
    - Better categorization
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'CLI_CASE',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='ae_hosp_events',
        verbose_name=_('Patient ID')
    )
    
    SEQUENCE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('Sequence Number'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # ADVERSE EVENT INFORMATION
    # ==========================================
    AENAME = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_('Incident')
    )
    
    AEDETAILS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Incident details')
    )
    
    AEDTC = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Date')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_Aehosp_Event'
        verbose_name = _('Adverse Event During Hospitalization')
        verbose_name_plural = _('Adverse Events During Hospitalization')
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'SEQUENCE'], name='idx_ae_subj_seq'),
            models.Index(fields=['USUBJID', 'AEDTC'], name='idx_ae_subj_date'),
            models.Index(fields=['AENAME'], name='idx_ae_name'),
            models.Index(fields=['AEDTC'], name='idx_ae_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_ae_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'SEQUENCE'],
                name='unique_ae_sequence'
            ),
        ]
    
    def __str__(self):
        return f"{self.AENAME} (#{self.SEQUENCE}) - {self.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related CLI_CASE"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    @property
    def days_after_admission(self):
        """Calculate days from admission to adverse event"""
        if self.AEDTC and self.USUBJID and self.USUBJID.ADMISDATE:
            delta = self.AEDTC - self.USUBJID.ADMISDATE
            return delta.days
        return None
    
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Event name is required
        if not self.AENAME or not self.AENAME.strip():
            errors['AENAME'] = _('Adverse event name is required and cannot be empty')
        
        # Validate event date
        if self.AEDTC:
            if self.AEDTC > date.today():
                errors['AEDTC'] = _('Event date cannot be in the future')
            
            # Event should be after admission
            if self.USUBJID and self.USUBJID.ADMISDATE:
                if self.AEDTC < self.USUBJID.ADMISDATE:
                    errors['AEDTC'] = _(
                        'Event date cannot be before admission date'
                    )
        
        # Validate sequence
        if self.SEQUENCE is not None and self.SEQUENCE < 1:
            errors['SEQUENCE'] = _('Sequence number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Auto-generate sequence if not provided"""
        # Strip whitespace
        if self.AENAME:
            self.AENAME = self.AENAME.strip()
        
        if self.AEDETAILS:
            self.AEDETAILS = self.AEDETAILS.strip()
        
        # Auto-generate sequence if not provided
        if self.SEQUENCE is None and self.USUBJID:
            from django.db.models import Max
            
            max_sequence = (
                AEHospEvent.objects
                .filter(USUBJID=self.USUBJID)
                .aggregate(Max('SEQUENCE'))['SEQUENCE__max']
            )
            self.SEQUENCE = (max_sequence + 1) if max_sequence else 1
        
        # Clear cache
        if hasattr(self, '_siteid_cache'):
            del self._siteid_cache
        
        super().save(*args, **kwargs)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    @classmethod
    def bulk_create_for_patient(cls, usubjid, event_list, user=None):
        """
        Efficiently create multiple adverse event records
        
        Args:
            usubjid: CLI_CASE instance
            event_list: List of dicts [{'AENAME': ..., 'AEDTC': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created AEHospEvent instances
        """
        from django.db.models import Max
        
        # Get current max sequence
        max_sequence = (
            cls.objects
            .filter(USUBJID=usubjid)
            .aggregate(Max('SEQUENCE'))['SEQUENCE__max']
        ) or 0
        
        # Prepare instances
        instances = []
        for i, event_data in enumerate(event_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                SEQUENCE=max_sequence + i,
                **event_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_patient_ae_events(cls, usubjid):
        """Get all adverse events for a patient"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('SEQUENCE')
    
    @classmethod
    def get_by_event_name(cls, event_name):
        """Get all occurrences of a specific adverse event"""
        return cls.objects.filter(
            AENAME__icontains=event_name
        ).select_related('USUBJID').order_by('AEDTC')
    
    @classmethod
    def get_recent_events(cls, days=7):
        """Get adverse events from the last N days"""
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days)
        return cls.objects.filter(
            AEDTC__gte=cutoff_date
        ).select_related('USUBJID').order_by('-AEDTC')