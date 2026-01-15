# backends/studies/study_43en/models/patient/PER_DATA.py

"""
Personal Data Models - Separated for Better Security
=====================================================

CRITICAL SECURITY NOTES:
- These models contain PII (Personally Identifiable Information)
- All sensitive fields use EncryptedCharField (django-fernet-encrypted-fields)
- OneToOne relationship with ENR_CASE/ENR_CONTACT
- Separate database routing recommended for production
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from encrypted_fields.fields import EncryptedCharField
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


# ==========================================
# PATIENT PERSONAL DATA
# ==========================================

class PERSONAL_DATA(AuditFieldsMixin):
    """
    Patient Personal Identifiable Information (PII)
    
    Separated from ENR_CASE for:
    - Enhanced security and encryption
    - Better access control
    - Easier compliance with data protection regulations
    - Potential separate database routing
    
    OneToOne relationship with ENR_CASE
    """
    
    # ==========================================
    # PRIMARY KEY (OneToOne with ENR_CASE)
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='USUBJID',
        verbose_name=_('Patient ID'),
        related_name='personal_data'
    )
    
    # ==========================================
    # PERSONAL IDENTIFIERS (ENCRYPTED)
    # ==========================================
    FULLNAME = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Full Name'),
        help_text=_('Patient full name (encrypted)')
    )
    
    PHONE = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Phone Number'),
        help_text=_('Contact phone number (encrypted)')
    )
    
    MEDRECORDID = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Medical Record Number'),
        help_text=_('Hospital medical record ID (encrypted)')
    )
    
    # ==========================================
    # ADDRESS INFORMATION (NEW SYSTEM)
    # ==========================================
    HOUSE_NUMBER_NEW = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('House Number/Building Details (New Administrative Division)'),
        help_text=_('House number, building, apartment details (new system, encrypted)')
    )
    
    STREET_NEW = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Street/Road Name (New Administrative Division)'),
        help_text=_('Street name under new administrative structure')
    )
    
    WARD_NEW = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Ward/Commune (New Administrative Division)'),
        help_text=_('Ward/commune under new administrative structure')
    )
    
    CITY_NEW = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('City/Province (New Administrative Division)'),
        help_text=_('City/province under new administrative structure')
    )
    
    # ==========================================
    # ADDRESS INFORMATION (OLD SYSTEM)
    # ==========================================
    HOUSE_NUMBER = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('House Number/Building Details (Old Administrative Division)'),
        help_text=_('House number, building, apartment details (old system, encrypted)')
    )
    
    STREET = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Street/Road Name (Old Administrative Division)'),
        help_text=_('Street name under old administrative structure')
    )
    
    WARD = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Ward/Commune (Old Administrative Division)'),
        help_text=_('Ward/commune under old administrative structure')
    )
    
    DISTRICT = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('District/County (Old Administrative Division)'),
        help_text=_('District under old administrative structure')
    )
    
    PROVINCECITY = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Province/City (Old Administrative Division)'),
        help_text=_('Province/city under old administrative structure')
    )
    
    # ==========================================
    # ADDRESS SYSTEM INDICATOR
    # ==========================================
    PRIMARY_ADDRESS = models.CharField(
        max_length=10,
        choices=[
            ('new', _('New Address')),
            ('old', _('Old Address')),
            ('both', _('Both Addresses'))
        ],
        null=True,
        blank=True,
        verbose_name=_('Primary Address System'),
        help_text=_('Which address system to use as primary')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'PERSONAL_DATA'
        verbose_name = _('Patient Personal Data')
        verbose_name_plural = _('Patient Personal Data')
        indexes = [
            # NO INDEXES on encrypted fields for security
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_pdata_modified'),
        ]
    
    def __str__(self):
        return f"Personal Data for {self.USUBJID.USUBJID.USUBJID}"
    
    # ==========================================
    # PROPERTIES (Decrypted on-the-fly)
    # ==========================================
    
    @property
    def full_address_new(self):
        """Get new full address (decrypted)"""
        parts = [self.HOUSE_NUMBER_NEW, self.STREET_NEW, self.WARD_NEW, self.CITY_NEW]
        result = ', '.join(filter(None, parts))
        return result if result else None
    
    @property
    def full_address_old(self):
        """Get old full address (decrypted)"""
        parts = [self.HOUSE_NUMBER, self.STREET, self.WARD, self.DISTRICT, self.PROVINCECITY]
        result = ', '.join(filter(None, parts))
        return result if result else None
    
    @property
    def geographic_location(self):
        """Get formatted geographic location based on primary address"""
        if self.PRIMARY_ADDRESS == 'new' or self.PRIMARY_ADDRESS == 'both':
            if self.full_address_new:
                return self.full_address_new
        
        # Fallback to old address
        return self.full_address_old
    
    def clean(self):
        """Basic validation - allow all fields to be optional"""
        # No strict validation - allow saving with minimal data
        pass