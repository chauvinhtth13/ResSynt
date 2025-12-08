from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class ImproveSympt(AuditFieldsMixin):
    """
    Symptom improvement tracking
    Documents improvement in initial symptoms over time
    
    Optimizations:
    - Added AuditFieldsMixin
    - Auto-incrementing SEQUENCE
    - Validation for dates and logic
    - Better indexes
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
        related_name='improve_symptoms',
        verbose_name=_('Patient ID')
    )
    
    SEQUENCE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('Sequence Number'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # IMPROVEMENT INFORMATION
    # ==========================================
    # IMPROVE_SYMPTS = models.CharField(
    #     max_length=3,
    #     choices=YesNoChoices.choices,
    #     db_index=True,
    #     verbose_name=_('Initial Symptoms Improved?')
    # )
    
    SYMPTS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Symptoms')
    )
    
    IMPROVE_CONDITIONS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Improvement Conditions')
    )
    
    SYMPTSDTC = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Assessment Date')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_Improve_Sympt'
        verbose_name = _('Symptom Improvement')
        verbose_name_plural = _('Symptom Improvements')
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'SEQUENCE'], name='idx_is_subj_seq'),
            models.Index(fields=['USUBJID', 'SYMPTSDTC'], name='idx_is_subj_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_is_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'SEQUENCE'],
                name='unique_improve_sequence'
            ),
        ]
    
    def __str__(self):
        return f"Symptom Assessment (#{self.SEQUENCE}) - {self.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related CLI_CASE"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    @property
    def is_improved(self):
        """Check if symptoms improved"""
        return bool(self.SYMPTS or self.IMPROVE_CONDITIONS)
    
    @property
    def days_since_admission(self):
        """Calculate days from admission to assessment"""
        if self.SYMPTSDTC and self.USUBJID and self.USUBJID.ADMISDATE:
            delta = self.SYMPTSDTC - self.USUBJID.ADMISDATE
            return delta.days
        return None
    
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Validate assessment date
        if self.SYMPTSDTC:
            if self.SYMPTSDTC > date.today():
                errors['SYMPTSDTC'] = _('Assessment date cannot be in the future')
            
            # Assessment should be after admission
            if self.USUBJID and self.USUBJID.ADMISDATE:
                if self.SYMPTSDTC < self.USUBJID.ADMISDATE:
                    errors['SYMPTSDTC'] = _(
                        'Assessment date cannot be before admission date'
                    )
        
        # Validate sequence
        if self.SEQUENCE is not None and self.SEQUENCE < 1:
            errors['SEQUENCE'] = _('Sequence number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Auto-generate sequence if not provided"""
        # Strip whitespace from text fields
        if self.SYMPTS:
            self.SYMPTS = self.SYMPTS.strip()
        
        if self.IMPROVE_CONDITIONS:
            self.IMPROVE_CONDITIONS = self.IMPROVE_CONDITIONS.strip()
        
        # Auto-generate sequence if not provided
        if self.SEQUENCE is None and self.USUBJID:
            from django.db.models import Max
            
            max_sequence = (
                ImproveSympt.objects
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
    def bulk_create_for_patient(cls, usubjid, improvement_list, user=None):
        """
        Efficiently create multiple improvement records
        
        Args:
            usubjid: CLI_CASE instance
            improvement_list: List of dicts [{'SYMPTS': ..., 'SYMPTSDTC': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created ImproveSympt instances
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
        for i, improvement_data in enumerate(improvement_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                SEQUENCE=max_sequence + i,
                **improvement_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_patient_improvements(cls, usubjid):
        """Get all improvement assessments for a patient"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('SEQUENCE')
    
    @classmethod
    def get_improved_patients(cls):
        """Get all patients with documented symptoms or improvement conditions"""
        return cls.objects.filter(
            models.Q(SYMPTS__isnull=False) | models.Q(IMPROVE_CONDITIONS__isnull=False)
        ).select_related('USUBJID').order_by('SYMPTSDTC')