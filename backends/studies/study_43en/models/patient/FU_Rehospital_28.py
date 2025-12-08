from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class Rehospitalization(AuditFieldsMixin):
    """
    Rehospitalization records during 28-day follow-up
     ONLY RENAMED FIELDS - NO LOGIC CHANGES
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'FU_CASE_28',
        on_delete=models.CASCADE,
        related_name='rehospitalizations',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    REHOSP_No = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('No.'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # REHOSPITALIZATION INFORMATION
    # ==========================================
    ReHospDate = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Readmitted Date')
    )
    
    ReHospReason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason')
    )
    
    ReHospLocate = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Hospital')
    )
    
    REHOSPDAYS = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Duration')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'FU_Rehospitalization_28'
        verbose_name = _('Rehospitalization (Day 28)')
        verbose_name_plural = _('Rehospitalizations (Day 28)')
        ordering = ['USUBJID', 'REHOSP_No']
        indexes = [
            models.Index(fields=['USUBJID', 'REHOSP_No'], name='idx_rh_subj_ep'),
            models.Index(fields=['ReHospDate'], name='idx_rh_date'),
            models.Index(fields=['USUBJID', 'ReHospDate'], name='idx_rh_subj_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_rh_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'REHOSP_No'],
                name='unique_rehosp_episode'
            ),
        ]
    
    def __str__(self):
        date_str = self.ReHospDate.strftime('%Y-%m-%d') if self.ReHospDate else 'No date'
        return f"Episode {self.REHOSP_No}: {date_str} - {self.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related FU_CASE_28"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    @property
    def days_after_enrollment(self):
        """Calculate days from enrollment to rehospitalization"""
        if self.ReHospDate and self.USUBJID and self.USUBJID.USUBJID and self.USUBJID.USUBJID.ENRDATE:
            delta = self.ReHospDate - self.USUBJID.USUBJID.ENRDATE
            return delta.days
        return None
    
    def clean(self):
        """Enhanced validation - MINIMAL (Day 28)"""
        errors = {}
        
        # Validate episode
        if self.REHOSP_No is not None and self.REHOSP_No < 1:
            errors['REHOSP_No'] = _('Episode number must be positive (≥1)')
        
        #  REMOVED: Date validation moved to form-level for better UX
        # Model-level validation is too strict and causes confusion
        # Let forms handle business logic validation with proper error messages
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Save with data cleanup - EPISODE auto-increment DISABLED"""
        # Strip whitespace
        if self.ReHospReason:
            self.ReHospReason = self.ReHospReason.strip()
        
        if self.ReHospLocate:
            self.ReHospLocate = self.ReHospLocate.strip()
        
        if self.REHOSPDAYS:
            self.REHOSPDAYS = self.REHOSPDAYS.strip()
        
        #  REMOVED: Auto-generate episode (now handled by JavaScript in form)
        # Users set EPISODE manually via form, no auto-increment on save
        
        # Clear cache
        if hasattr(self, '_siteid_cache'):
            del self._siteid_cache
        
        super().save(*args, **kwargs)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    @classmethod
    def bulk_create_for_patient(cls, usubjid, rehosp_list, user=None):
        """
        Efficiently create multiple rehospitalization records
        
        Args:
            usubjid: FU_CASE_28 instance
            rehosp_list: List of dicts [{'ReHospDate': ..., 'ReHospReason': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created Rehospitalization instances
        """
        from django.db.models import Max
        
        # Get current max episode
        max_episode = (
            cls.objects
            .filter(USUBJID=usubjid)
            .aggregate(Max('REHOSP_No'))['REHOSP_No__max']
        ) or 0
        
        # Prepare instances
        instances = []
        for i, rehosp_data in enumerate(rehosp_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                REHOSP_No=max_episode + i,
                **rehosp_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_patient_rehospitalizations(cls, usubjid):
        """Get all rehospitalizations for a patient"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('REHOSP_No')
    
    @classmethod
    def get_recent_rehospitalizations(cls, days=7):
        """Get recent rehospitalizations"""
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days)
        return cls.objects.filter(
            ReHospDate__gte=cutoff_date
        ).select_related('USUBJID').order_by('-ReHospDate')