
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date
class ContactMedicationHistory28(AuditFieldsMixin):
    """
    Medication history for contact follow-up at Day 28
    Tracks medication use episodes
    
    Optimizations:
    - Added AuditFieldsMixin
    - Validation for required fields
    - Bulk operations support
    - Query helper methods
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'FU_CONTACT_28',
        on_delete=models.CASCADE,
        related_name='medications',
        db_column='USUBJID',
        verbose_name=_('Follow-up Day 28')
    )
    
    EPISODE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('Episode Number'),
        help_text=_('Medication episode number')
    )
    
    # ==========================================
    # MEDICATION INFORMATION
    # ==========================================
    MEDICATION_NAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Medication Name')
    )
    
    DOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Dosage')
    )
    
    USAGE_PERIOD = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Usage Period')
    )
    
    REASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Usage Reason')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'Contact_Medication_history_28'
        verbose_name = _('Contact Medication History (Day 28)')
        verbose_name_plural = _('Contact Medication Histories (Day 28)')
        ordering = ['USUBJID', 'EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_cmh28_subj_ep'),
            models.Index(fields=['MEDICATION_NAME'], name='idx_cmh28_name'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_cmh28_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'EPISODE'],
                name='unique_contact_med28_episode'
            ),
        ]
    
    def __str__(self):
        med_name = self.MEDICATION_NAME or 'Unknown'
        return f"Episode {self.EPISODE}: {med_name} - {self.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related FU_CONTACT_28"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    def clean(self):
        """Enhanced validation - MINIMAL"""
        errors = {}
        
        # Validate episode
        if self.EPISODE is not None and self.EPISODE < 1:
            errors['EPISODE'] = _('Episode number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Save with data cleanup"""
        # Strip whitespace
        if self.MEDICATION_NAME:
            self.MEDICATION_NAME = self.MEDICATION_NAME.strip()
        
        if self.DOSAGE:
            self.DOSAGE = self.DOSAGE.strip()
        
        if self.USAGE_PERIOD:
            self.USAGE_PERIOD = self.USAGE_PERIOD.strip()
        
        if self.REASON:
            self.REASON = self.REASON.strip()
        
        # Clear cache
        if hasattr(self, '_siteid_cache'):
            del self._siteid_cache
        
        super().save(*args, **kwargs)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    @classmethod
    def bulk_create_for_contact(cls, usubjid, medication_list, user=None):
        """
        Efficiently create multiple medication records
        
        Args:
            usubjid: FU_CONTACT_28 instance
            medication_list: List of dicts with medication data
            user: User object for audit trail
        
        Returns:
            List of created ContactMedicationHistory28 instances
        """
        from django.db.models import Max
        
        # Get current max episode
        max_episode = (
            cls.objects
            .filter(USUBJID=usubjid)
            .aggregate(Max('EPISODE'))['EPISODE__max']
        ) or 0
        
        # Prepare instances
        instances = []
        for i, med_data in enumerate(medication_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                EPISODE=max_episode + i,
                **med_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_contact_medications(cls, usubjid):
        """Get all medications for a contact"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('EPISODE')
    
    @classmethod
    def get_by_medication_name(cls, medication_name):
        """Get all records for a specific medication"""
        return cls.objects.filter(
            MEDICATION_NAME__icontains=medication_name
        ).select_related('USUBJID')


class ContactMedicationHistory90(AuditFieldsMixin):
    """
    Medication history for contact follow-up at Day 90
    Tracks medication use episodes at extended follow-up
    
    Optimizations:
    - Added AuditFieldsMixin
    - Validation for required fields
    - Bulk operations support
    - Query helper methods
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'FU_CONTACT_90',
        on_delete=models.CASCADE,
        related_name='medications',
        db_column='USUBJID',
        verbose_name=_('Follow-up Day 90')
    )
    
    EPISODE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('Episode Number'),
        help_text=_('Medication episode number')
    )
    
    # ==========================================
    # MEDICATION INFORMATION
    # ==========================================
    MEDICATION_NAME = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Medication Name')
    )
    
    DOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Dosage')
    )
    
    USAGE_PERIOD = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Usage Period')
    )
    
    REASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Usage Reason')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'Contact_Medication_history_90'
        verbose_name = _('Contact Medication History (Day 90)')
        verbose_name_plural = _('Contact Medication Histories (Day 90)')
        ordering = ['USUBJID', 'EPISODE']
        indexes = [
            models.Index(fields=['USUBJID', 'EPISODE'], name='idx_cmh90_subj_ep'),
            models.Index(fields=['MEDICATION_NAME'], name='idx_cmh90_name'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_cmh90_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'EPISODE'],
                name='unique_contact_med90_episode'
            ),
        ]
    
    def __str__(self):
        med_name = self.MEDICATION_NAME or 'Unknown'
        return f"Episode {self.EPISODE}: {med_name} - {self.USUBJID_id} (Day 90)"
    
    @property
    def SITEID(self):
        """Get SITEID from related FU_CONTACT_90"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    def clean(self):
        """Enhanced validation - MINIMAL"""
        errors = {}
        
        # Validate episode
        if self.EPISODE is not None and self.EPISODE < 1:
            errors['EPISODE'] = _('Episode number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Save with data cleanup"""
        # Strip whitespace
        if self.MEDICATION_NAME:
            self.MEDICATION_NAME = self.MEDICATION_NAME.strip()
        
        if self.DOSAGE:
            self.DOSAGE = self.DOSAGE.strip()
        
        if self.USAGE_PERIOD:
            self.USAGE_PERIOD = self.USAGE_PERIOD.strip()
        
        if self.REASON:
            self.REASON = self.REASON.strip()
        
        # Clear cache
        if hasattr(self, '_siteid_cache'):
            del self._siteid_cache
        
        super().save(*args, **kwargs)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    @classmethod
    def bulk_create_for_contact(cls, usubjid, medication_list, user=None):
        """
        Efficiently create multiple medication records
        
        Args:
            usubjid: FU_CONTACT_90 instance
            medication_list: List of dicts with medication data
            user: User object for audit trail
        
        Returns:
            List of created ContactMedicationHistory90 instances
        """
        from django.db.models import Max
        
        # Get current max episode
        max_episode = (
            cls.objects
            .filter(USUBJID=usubjid)
            .aggregate(Max('EPISODE'))['EPISODE__max']
        ) or 0
        
        # Prepare instances
        instances = []
        for i, med_data in enumerate(medication_list, start=1):
            instance = cls(
                USUBJID=usubjid,
                EPISODE=max_episode + i,
                **med_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_contact_medications(cls, usubjid):
        """Get all medications for a contact"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('EPISODE')
    
    @classmethod
    def get_by_medication_name(cls, medication_name):
        """Get all records for a specific medication"""
        return cls.objects.filter(
            MEDICATION_NAME__icontains=medication_name
        ).select_related('USUBJID')