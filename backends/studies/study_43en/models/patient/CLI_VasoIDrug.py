from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class VasoIDrug(AuditFieldsMixin):
    """
    Vasoactive and inotropic drug usage
    Tracks vasopressor and inotrope administration
    
    Optimizations:
    - Added AuditFieldsMixin
    - Auto-incrementing SEQUENCE
    - Duration stored as CharField
    - Validation for dosage and duration
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
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='vaso_drugs',
        verbose_name=_('Patient ID')
    )
    
    SEQUENCE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('Sequence Number'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # DRUG INFORMATION
    # ==========================================
    VASOIDRUGNAME = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_('Drug Name')
    )
    
    VASOIDOSE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Total dose (µg/kg/min)')
    )
    
    VASOIDURATION = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Duration (days)')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_Vasoi_Drug'
        verbose_name = _('Vasoactive Drug')
        verbose_name_plural = _('Vasoactive Drugs')
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'SEQUENCE'], name='idx_vd_subj_seq'),
            models.Index(fields=['VASOIDRUGNAME'], name='idx_vd_drugname'),
            models.Index(fields=['VASOIDURATION'], name='idx_vd_duration'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_vd_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'SEQUENCE'],
                name='unique_vaso_sequence'
            ),
        ]
    
    def __str__(self):
        dosage = f" - {self.VASOIDOSE}" if self.VASOIDOSE else ""
        return f"{self.VASOIDRUGNAME}{dosage} (#{self.SEQUENCE})"
    
    @property
    def SITEID(self):
        """Get SITEID from related CLI_CASE"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    @property
    def duration_days(self):
        """
        Get drug administration duration in days
        Now stored as CharField in VASOIDURATION
        """
        if self.VASOIDURATION:
            try:
                return int(self.VASOIDURATION)
            except (ValueError, TypeError):
                return None
        return None
    
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Drug name is required
        if not self.VASOIDRUGNAME or not self.VASOIDRUGNAME.strip():
            errors['VASOIDRUGNAME'] = _('Drug name is required and cannot be empty')
        
        # Validate duration format if provided
        if self.VASOIDURATION:
            try:
                duration_val = int(self.VASOIDURATION)
                if duration_val < 0:
                    errors['VASOIDURATION'] = _('Duration must be a positive number')
            except (ValueError, TypeError):
                errors['VASOIDURATION'] = _('Duration must be a valid number')
        
        # Validate sequence
        if self.SEQUENCE is not None and self.SEQUENCE < 1:
            errors['SEQUENCE'] = _('Sequence number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Auto-generate sequence if not provided"""
        # Strip whitespace
        if self.VASOIDRUGNAME:
            self.VASOIDRUGNAME = self.VASOIDRUGNAME.strip()
        
        if self.VASOIDOSE:
            self.VASOIDOSE = self.VASOIDOSE.strip()
        
        if self.VASOIDURATION:
            self.VASOIDURATION = self.VASOIDURATION.strip()
        
        # Auto-generate sequence if not provided
        if self.SEQUENCE is None and self.USUBJID:
            from django.db.models import Max
            
            max_sequence = (
                VasoIDrug.objects
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
    def bulk_create_for_patient(cls, usubjid, drug_list, user=None):
        """
        Efficiently create multiple vasoactive drug records
        
        Args:
            usubjid: CLI_CASE instance
            drug_list: List of dicts [{'VASOIDRUGNAME': ..., 'VASOIDOSE': ..., 'VASOIDURATION': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created VasoIDrug instances
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
        for i, drug_data in enumerate(drug_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                SEQUENCE=max_sequence + i,
                **drug_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_patient_vaso_drugs(cls, usubjid):
        """Get all vasoactive drugs for a patient"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('SEQUENCE')
    
    @classmethod
    def get_by_drug_name(cls, drug_name):
        """Get usage statistics for a specific drug"""
        return cls.objects.filter(
            VASOIDRUGNAME__icontains=drug_name
        ).select_related('USUBJID')