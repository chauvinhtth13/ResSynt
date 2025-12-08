# backends/studies/study_43en/models/contact/MedHistory.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


class ENR_CONTACT_MedHisDrug(AuditFieldsMixin):
    """
    Contact medication history
    
    Similar to patient medication but for contacts
    
    Inherits from AuditFieldsMixin:
    - version, last_modified_by_id, last_modified_by_username, last_modified_at
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'ENR_CONTACT',
        on_delete=models.CASCADE,
        related_name='medhisdrug_set',
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Contact')
    )
    
    SEQUENCE = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Sequence Number'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # DRUG INFORMATION
    # ==========================================
    DRUGNAME = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_('Drug Name'),
        help_text=_('Generic or brand name of the medication')
    )
    
    DOSAGE = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Dosage'),
        help_text=_('e.g., "500mg", "10ml", "2 tablets"')
    )
    
    USAGETIME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Usage Duration'),
        help_text=_('How long the medication was taken')
    )
    
    USAGEREASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Usage Reason'),
        help_text=_('Medical condition or reason for taking this medication')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'Contact_ENR_History_Drug'
        verbose_name = _('Contact Drug History')
        verbose_name_plural = _('Contact Drug Histories')
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'SEQUENCE'], name='idx_cmed_subj_seq'),  
            models.Index(fields=['DRUGNAME'], name='idx_cmed_drugname'),  
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_cmed_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'SEQUENCE'],
                name='unique_cmed_sequence' 
            )
        ]
    
    def __str__(self):
        drug_name = self.DRUGNAME or 'N/A'
        return f"{self.USUBJID.USUBJID} - {drug_name}" if self.USUBJID else f"Drug: {drug_name}"
    
    @property
    def SITEID(self):
        """Get SITEID from related ENR_CONTACT (with caching)"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    def clean(self):
        """Validation"""
        errors = {}
        
        # Drug name is required and must not be empty
        if not self.DRUGNAME or not self.DRUGNAME.strip():
            errors['DRUGNAME'] = _('Drug name is required and cannot be empty')
        
        # Validate sequence if provided
        if self.SEQUENCE is not None and self.SEQUENCE < 1:
            errors['SEQUENCE'] = _('Sequence number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Auto-generate sequence if not provided"""
        # Strip whitespace from drug name
        if self.DRUGNAME:
            self.DRUGNAME = self.DRUGNAME.strip()
        
        # Auto-generate sequence if not provided
        if self.SEQUENCE is None and self.USUBJID:
            from django.db.models import Max
            
            max_sequence = (
                ENR_CONTACT_MedHisDrug.objects
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
    def bulk_create_for_contact(cls, usubjid, drug_list, user=None):
        """
        Efficiently create multiple drug history records for contact
        
        Args:
            usubjid: ENR_CONTACT instance
            drug_list: List of dicts with drug info
            user: User object for audit trail
        
        Returns:
            List of created ENR_CONTACT_MedHisDrug instances
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
    def get_contact_drug_history(cls, usubjid):
        """Get all medications for contact with optimal query"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).select_related('USUBJID').order_by('SEQUENCE')