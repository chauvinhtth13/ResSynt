# backends/studies/study_44en/models/HH_PERSONAL_DATA.py

"""
Household Personal Data - Separated for Better Security
========================================================

CRITICAL SECURITY NOTES:
- This model contains PII (Personally Identifiable Information)
- All sensitive fields use EncryptedCharField (django-fernet-encrypted-fields)
- OneToOne relationship with HH_CASE
- Separate database routing recommended for production
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_fields.fields import EncryptedCharField
from backends.studies.study_44en.models.base_models import AuditFieldsMixin


class HH_PERSONAL_DATA(AuditFieldsMixin):
    """
    Household Personal Identifiable Information (PII)
    
    Separated from HH_CASE for:
    - Enhanced security and encryption
    - Better access control
    - Easier compliance with data protection regulations
    - Potential separate database routing
    
    OneToOne relationship with HH_CASE
    """
    
    # ==========================================
    # PRIMARY KEY (OneToOne with HH_CASE)
    # ==========================================
    HHID = models.OneToOneField(
        'HH_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='HHID',
        db_column='HHID',
        verbose_name=_('Household ID'),
        related_name='personal_data'
    )
    
    # ==========================================
    # ADDRESS INFORMATION (ENCRYPTED)
    # ==========================================
    STREET = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Street/Road/Block'),
        help_text=_('Street address (encrypted)')
    )
    
    WARD = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Ward/Commune'),
        help_text=_('Ward or commune (encrypted)')
    )
    
    CITY = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('City'),
        help_text=_('City (encrypted)')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'HH_PERSONAL_DATA'
        verbose_name = _('Household Personal Data')
        verbose_name_plural = _('Household Personal Data')
        indexes = [
            # NO INDEXES on encrypted fields for security
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_hhpdata_modified'),
        ]
    
    def __str__(self):
        return f"Personal Data for {self.HHID_id}"
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    
    @property
    def full_address(self):
        """Get full address (decrypted)"""
        parts = [self.STREET, self.WARD, self.CITY]
        result = ', '.join(filter(None, parts))
        return result if result else None
    
    def clean(self):
        """Basic validation - allow all fields to be optional"""
        pass