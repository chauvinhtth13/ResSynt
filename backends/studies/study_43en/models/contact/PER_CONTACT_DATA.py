# backends/studies/study_43en/models/contact/PER_CONTACT_DATA.py

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
# CONTACT PERSONAL DATA
# ==========================================

class PERSONAL_CONTACT_DATA(AuditFieldsMixin):
    """
    Contact Personal Identifiable Information (PII)
    
    Similar to PERSONAL_DATA but for contacts
    Simpler structure (no address, no medical record ID)
    
    OneToOne relationship with ENR_CONTACT
    """
    
    # ==========================================
    # PRIMARY KEY (OneToOne with ENR_CONTACT)
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CONTACT',
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='USUBJID',
        verbose_name=_('Contact ID'),
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
        help_text=_('Contact full name (encrypted)')
    )
    
    PHONE = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Phone Number'),
        help_text=_('Contact phone number (encrypted)')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'PERSONAL_CONTACT_DATA'
        verbose_name = _('Contact Personal Data')
        verbose_name_plural = _('Contact Personal Data')
        indexes = [
            # NO INDEXES on encrypted fields for security
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_pcdata_modified'),
        ]
    
    def __str__(self):
        return f"Personal Data for Contact {self.USUBJID.USUBJID.USUBJID}"
    
    def clean(self):
        """
        Validation - simpler than patient
        At least name or phone should be provided
        """
        if not self.FULLNAME and not self.PHONE:
            raise ValidationError(
                _('At least full name or phone number must be provided')
            )