from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class HospiProcess(AuditFieldsMixin):
    """
    Hospitalization process tracking
    Documents patient transfers between departments
    
    Optimizations:
    - Added AuditFieldsMixin
    - Auto-incrementing SEQUENCE
    - Validation for dates
    - Duration calculation
    - Bulk operations support
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'CLI_CASE',
        db_column='USUBJID',
        to_field='USUBJID',
        on_delete=models.CASCADE,
        related_name='hospiprocesses',
        verbose_name=_('Patient ID')
    )
    
    SEQUENCE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('Sequence Number'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # DEPARTMENT INFORMATION
    # ==========================================
    DEPTNAME = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_('Department')
    )
    
    STARTDTC = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Start Date')
    )
    
    ENDDTC = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('End Date')
    )
    
    TRANSFER_REASON = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Reason')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_Hospi_Process'
        verbose_name = _('Hospitalization Process')
        verbose_name_plural = _('Hospitalization Processes')
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'SEQUENCE'], name='idx_hp_subj_seq'),
            models.Index(fields=['USUBJID', 'STARTDTC'], name='idx_hp_subj_start'),
            models.Index(fields=['DEPTNAME'], name='idx_hp_dept'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_hp_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'SEQUENCE'],
                name='unique_hospi_sequence'
            ),
            # End date must be after start date
            models.CheckConstraint(
                check=(
                    models.Q(STARTDTC__isnull=True) |
                    models.Q(ENDDTC__isnull=True) |
                    models.Q(ENDDTC__gte=models.F('STARTDTC'))
                ),
                name='hp_end_after_start'
            ),
        ]
    
    def __str__(self):
        return f"{self.DEPTNAME} (#{self.SEQUENCE}) - {self.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related CLI_CASE"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    @property
    def duration_days(self):
        """Calculate stay duration in days"""
        if self.STARTDTC and self.ENDDTC:
            delta = self.ENDDTC - self.STARTDTC
            return delta.days
        return None

    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Department name is required
        if not self.DEPTNAME or not self.DEPTNAME.strip():
            errors['DEPTNAME'] = _('Department name is required and cannot be empty')
        
        # Validate dates
        if self.STARTDTC and self.ENDDTC:
            if self.ENDDTC < self.STARTDTC:
                errors['ENDDTC'] = _('End date cannot be before start date')
        
        if self.STARTDTC and self.STARTDTC > date.today():
            errors['STARTDTC'] = _('Start date cannot be in the future')
        
        if self.ENDDTC and self.ENDDTC > date.today():
            errors['ENDDTC'] = _('End date cannot be in the future')
        
        # Validate sequence
        if self.SEQUENCE is not None and self.SEQUENCE < 1:
            errors['SEQUENCE'] = _('Sequence number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Auto-generate sequence if not provided"""
        # Strip whitespace
        if self.DEPTNAME:
            self.DEPTNAME = self.DEPTNAME.strip()
        
        if self.TRANSFER_REASON:
            self.TRANSFER_REASON = self.TRANSFER_REASON.strip()
        
        # Auto-generate sequence if not provided
        if self.SEQUENCE is None and self.USUBJID:
            from django.db.models import Max
            
            max_sequence = (
                HospiProcess.objects
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
    def bulk_create_for_patient(cls, usubjid, process_list, user=None):
        """
        Efficiently create multiple hospitalization process records
        
        Args:
            usubjid: CLI_CASE instance
            process_list: List of dicts [{'DEPTNAME': ..., 'STARTDTC': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created HospiProcess instances
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
        for i, process_data in enumerate(process_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                SEQUENCE=max_sequence + i,
                **process_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_patient_timeline(cls, usubjid):
        """Get all departments with optimal query"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('SEQUENCE')
    
    @classmethod
    def get_current_departments(cls):
        """Get all patients currently in departments (no end date)"""
        return cls.objects.filter(
            ENDDTC__isnull=True
        ).select_related('USUBJID').order_by('STARTDTC')