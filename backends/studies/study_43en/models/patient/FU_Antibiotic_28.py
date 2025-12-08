from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


class FollowUpAntibiotic(AuditFieldsMixin):
    """
    Antibiotic usage during 28-day follow-up period
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
        related_name='antibiotics',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    Antb_Usage_No = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('No.'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # ANTIBIOTIC INFORMATION
    # ==========================================
    Antb_Name = models.CharField(
        max_length=255,
        null=True,        
        blank=True,        
        db_index=True,
        verbose_name=_('Antibiotics Name')
    )
    
    Antb_Usage_Reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason')
    )
    
    Antb_Usage_Date = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Duration')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'FU_Antibiotic_28'
        verbose_name = _('Follow-up Antibiotic (Day 28)')
        verbose_name_plural = _('Follow-up Antibiotics (Day 28)')
        ordering = ['USUBJID', 'Antb_Usage_No']
        indexes = [
            models.Index(fields=['USUBJID', 'Antb_Usage_No'], name='idx_fua_subj_ep'),
            models.Index(fields=['Antb_Name'], name='idx_fua_name'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_fua_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'Antb_Usage_No'],
                name='unique_fu_antibio_episode'
            ),
        ]
    
    def __str__(self):
        return f"Episode {self.Antb_Usage_No}: {self.Antb_Name} - {self.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related FU_CASE_28"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Antibiotic name is required
        if not self.Antb_Name or not self.Antb_Name.strip():
            errors['Antb_Name'] = _('Antibiotic name is required and cannot be empty')
        
        # Validate episode
        if self.Antb_Usage_No is not None and self.Antb_Usage_No < 1:
            errors['Antb_Usage_No'] = _('Episode number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Save method - EPISODE auto-increment DISABLED - now handled by JavaScript"""
        # Strip whitespace
        if self.Antb_Name:
            self.Antb_Name = self.Antb_Name.strip()
        
        if self.Antb_Usage_Reason:
            self.Antb_Usage_Reason = self.Antb_Usage_Reason.strip()
        
        if self.Antb_Usage_Date:
            self.Antb_Usage_Date = self.Antb_Usage_Date.strip()
        
        # EPISODE auto-increment DISABLED - now handled by JavaScript
        # The EPISODE field should be set by the frontend formset and not auto-generated on save
        
        # Clear cache
        if hasattr(self, '_siteid_cache'):
            del self._siteid_cache
        
        super().save(*args, **kwargs)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    @classmethod
    def bulk_create_for_patient(cls, usubjid, antibiotic_list, user=None):
        """
        Efficiently create multiple antibiotic records
        
        Args:
            usubjid: FU_CASE_28 instance
            antibiotic_list: List of dicts [{'Antb_Name': ..., 'Antb_Usage_Date': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created FollowUpAntibiotic instances
        """
        from django.db.models import Max
        
        # Get current max episode
        max_episode = (
            cls.objects
            .filter(USUBJID=usubjid)
            .aggregate(Max('Antb_Usage_No'))['Antb_Usage_No__max']
        ) or 0
        
        # Prepare instances
        instances = []
        for i, antibio_data in enumerate(antibiotic_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                Antb_Usage_No=max_episode + i,
                **antibio_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_patient_antibiotics(cls, usubjid):
        """Get all antibiotics for a patient"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('Antb_Usage_No')