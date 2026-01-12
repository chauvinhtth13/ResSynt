"""
Abstract base models for common fields across all CRF models

Provides audit trail, version control, and completion tracking
that should be present in all Clinical Research Form models.

Usage:
    from backends.studies.study_43en.models.base_models import AuditFieldsMixin
    
    class MyModel(AuditFieldsMixin):
        # Your model fields here
        pass
        
Author: Generated for 43EN Clinical Trial System
Date: 2025-10-23
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.study_site_manage import SiteFilteredManager


# ==========================================
# DEPARTMENT CHOICES BY SITE
# ==========================================



class AuditFieldsMixin(models.Model):
    """
    Abstract base model providing audit trail and version control
    
     UPDATED: Added site_objects manager for site filtering
    """
    
    # ==========================================
    # VERSION CONTROL (giữ nguyên)
    # ==========================================
    version = models.IntegerField(
        default=0,
        editable=False,
        help_text=_("Version number for optimistic locking")
    )
    
    # ==========================================
    # MODIFICATION TRACKING (giữ nguyên)
    # ==========================================
    last_modified_by_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        help_text=_("User ID who last modified this record")
    )
    
    last_modified_by_username = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=_("Username backup for audit trail")
    )
    
    last_modified_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text=_("Timestamp of last modification")
    )
    
    # ==========================================
    #  THÊM: MANAGERS
    # ==========================================
    objects = models.Manager()  # Default manager (no filtering)
    site_objects = SiteFilteredManager()  # Site-aware manager
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Giữ nguyên"""
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)
    
    def get_modification_info(self):
        """Giữ nguyên"""
        if self.last_modified_by_username:
            return {
                'user': self.last_modified_by_username,
                'user_id': self.last_modified_by_id,
                'timestamp': self.last_modified_at,
                'version': self.version
            }
        return None


class TimestampMixin(models.Model):
    """
    Lightweight mixin for creation/update timestamps
    
    Use this if you only need timestamps without full audit trail.
    For CRF models, prefer AuditFieldsMixin instead.
    
    Provides:
    - created_at: Auto-set on creation (auto_now_add=True)
    - updated_at: Auto-updated on save (auto_now=True)
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_('Created At'),
        help_text=_("Timestamp when record was created. Auto-set once, never changes.")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_("Timestamp when record was last updated. Auto-updated on every save().")
    )
    
    class Meta:
        abstract = True


class SiteFilteredMixin(models.Model):
    """
    Mixin for multi-site clinical trials
    
    Adds SITEID field for filtering data by study site.
    Useful for multi-center trials where each site should only
    see their own patients.
    
    Note: SCR_CASE already has SITEID, so don't inherit
    from both AuditFieldsMixin and SiteFilteredMixin.
    """
    SITEID = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name=_('Site ID'),
        help_text=_("Site identifier for multi-center study (e.g., 'HCM01', 'HN02')")
    )
    
    class Meta:
        abstract = True
