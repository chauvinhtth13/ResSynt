"""
Abstract base models for common fields across all CRF models

Provides audit trail, version control, and completion tracking
that should be present in all Clinical Research Form models.

Usage:
    from backends.studies.study_44en.models.base_models import AuditFieldsMixin
    
    class MyModel(AuditFieldsMixin):
        # Your model fields here
        pass
        
Author: Generated for 44EN Study
Date: 2025-10-23
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
import logging
import re

logger = logging.getLogger(__name__)

# Database alias constant for study_44en
DB_ALIAS = 'db_study_44en'

# Valid HHID patterns for security validation
VALID_HHID_PATTERN = re.compile(r'^44EN-\d{3}$')

# Cache for model field analysis (avoids repeated reflection)
_MODEL_FIELDS_CACHE = {}


def _validate_hhid(hhid):
    """
    SECURITY: Validate HHID format to prevent injection attacks
    
    Args:
        hhid: Household ID to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not hhid or hhid == 'all':
        return True
    
    if isinstance(hhid, str):
        # Pattern: 44EN-XXX where XXX is 3 digits
        return bool(VALID_HHID_PATTERN.match(hhid)) or hhid.isalnum()
    
    if isinstance(hhid, (list, tuple)):
        return all(_validate_hhid(h) for h in hhid)
    
    return False


def _get_cached_model_fields(model):
    """
    Get model fields with caching to avoid repeated reflection
    """
    model_name = model.__name__
    if model_name not in _MODEL_FIELDS_CACHE:
        _MODEL_FIELDS_CACHE[model_name] = frozenset(
            f.name for f in model._meta.get_fields()
        )
    return _MODEL_FIELDS_CACHE[model_name]


class SiteFilteredQuerySet(models.QuerySet):
    """
    Custom QuerySet with intelligent site/household filtering for Study 44EN
    
    Automatically detects model structure and applies appropriate filters:
    - Model có HHID field → filter trực tiếp
    - Model có MEMBERID → filter qua relationship chain
    """
    
    def filter_by_site(self, site_id):
        """
        Filter queryset by HHID (or related HHID for child models)
        
        Args:
            site_id: Can be:
                - None or 'all': Return all (no filter)
                - str: Single HHID ('44EN-001')
                - list/tuple: Multiple HHIDs (['44EN-001', '44EN-002'])
        
        Returns:
            Filtered QuerySet
        """
        # SECURITY: Validate input
        if not _validate_hhid(site_id):
            logger.error(f"[{self.model.__name__}] SECURITY: Invalid HHID format: {site_id}")
            return self.none()
        
        # No filter - return all
        if not site_id or site_id == 'all':
            logger.debug(f"[{self.model.__name__}] No filter (all)")
            return self
        
        model = self.model
        model_name = model.__name__
        model_fields = _get_cached_model_fields(model)
        
        # Normalize to list
        hhids = [site_id] if isinstance(site_id, str) else list(site_id)
        is_single = len(hhids) == 1
        single_hhid = hhids[0] if is_single else None
        
        # ==========================================
        # Strategy 1: Direct HHID field
        # ==========================================
        if 'HHID' in model_fields:
            logger.debug(f"[{model_name}] Filter via HHID field")
            if is_single:
                return self.filter(HHID=single_hhid)
            return self.filter(HHID__in=hhids)
        
        # ==========================================
        # Strategy 2: MEMBERID → HH_Member → HHID
        # ==========================================
        if 'MEMBERID' in model_fields:
            field = model._meta.get_field('MEMBERID')
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                logger.debug(f"[{model_name}] Filter via MEMBERID relationship")
                if is_single:
                    return self.filter(MEMBERID__HHID=single_hhid)
                return self.filter(MEMBERID__HHID__in=hhids)
        
        # ==========================================
        # No valid strategy - return empty for security
        # ==========================================
        logger.error(f"[{model_name}] No filtering strategy found")
        return self.none()


class SiteFilteredManager(models.Manager):
    """
    Custom Manager with site/household filtering capabilities for Study 44EN
    """
    
    def get_queryset(self):
        """Return custom queryset with site filtering"""
        return SiteFilteredQuerySet(self.model, using=self._db)
    
    def filter_by_site(self, site_id):
        """Filter queryset by HHID"""
        return self.get_queryset().filter_by_site(site_id)
    
    def using(self, alias):
        """Support database routing with method chaining"""
        return self.get_queryset().using(alias)


class AuditFieldsMixin(models.Model):
    """
    Abstract base model providing audit trail and version control
    
    Includes site_objects manager for site filtering
    """
    
    # ==========================================
    # VERSION CONTROL
    # ==========================================
    version = models.IntegerField(
        default=0,
        editable=False,
        help_text=_("Version number for optimistic locking")
    )
    
    # ==========================================
    # MODIFICATION TRACKING
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
    # MANAGERS
    # ==========================================
    objects = models.Manager()  # Default manager (no filtering)
    site_objects = SiteFilteredManager()  # Site-aware manager
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)
    
    def get_modification_info(self):
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
