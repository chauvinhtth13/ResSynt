"""
Tenancy Utilities - Optimized with two-layer caching.

Provides permission management, site access, and study tracking.
"""
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.utils import timezone

logger = logging.getLogger(__name__)


class TenancyUtils:
    """
    Centralized utility functions with two-layer caching.
    
    Layer 1: Django cache (Redis/Memcached)
    Layer 2: Database
    """
    
    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'tenancy_'
    
    # =========================================================================
    # Cache Helpers
    # =========================================================================
    
    @classmethod
    def _cache_key(cls, *parts) -> str:
        """Generate cache key."""
        key = '_'.join(str(p) for p in parts)
        if len(key) > 200:
            key = hashlib.md5(key.encode()).hexdigest()
        return f"{cls.CACHE_PREFIX}{key}"
    
    # =========================================================================
    # Permission Management
    # =========================================================================
    
    @classmethod
    def get_user_permissions(cls, user, study) -> Set[str]:
        """
        Get user permissions for a study.
        
        Returns:
            Set of permission codenames (e.g., {'add_patient', 'view_patient'})
        """
        if not user or not study:
            return set()
        
        cache_key = cls._cache_key('perms', user.pk, study.pk)
        permissions = cache.get(cache_key)
        
        if permissions is not None:
            return permissions
        
        try:
            from backends.tenancy.models import StudyMembership
            
            permissions = set()
            app_label = f'study_{study.code.lower()}'
            
            memberships = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            ).select_related('group').prefetch_related(
                Prefetch(
                    'group__permissions',
                    queryset=Permission.objects.filter(
                        content_type__app_label=app_label
                    ).only('codename', 'content_type_id')  # Only fetch needed fields
                )
            )
            
            for membership in memberships:
                for perm in membership.group.permissions.all():
                    if perm.content_type.app_label == app_label:
                        permissions.add(perm.codename)
            
            cache.set(cache_key, permissions, cls.CACHE_TTL)
            
        except Exception as e:
            logger.error(f"Error getting permissions: {type(e).__name__}")
            permissions = set()
        
        return permissions
    
    @classmethod
    def user_has_permission(cls, user, study, codename: str) -> bool:
        """Check if user has a specific permission."""
        return codename in cls.get_user_permissions(user, study)
    
    @classmethod
    def get_permission_display(cls, user, study) -> Dict[str, List[str]]:
        """Get permissions grouped by model."""
        permissions = cls.get_user_permissions(user, study)
        
        grouped: Dict[str, List[str]] = {}
        for perm in permissions:
            parts = perm.split('_', 1)
            if len(parts) == 2:
                action, model = parts
                grouped.setdefault(model, []).append(action)
        
        return grouped
    
    # =========================================================================
    # Site Access
    # =========================================================================
    
    @classmethod
    def get_user_sites(cls, user, study) -> List[str]:
        """Get sites user can access in a study."""
        if not user or not study:
            return []
        
        cache_key = cls._cache_key('sites', user.pk, study.pk)
        sites = cache.get(cache_key)
        
        if sites is not None:
            return sites
        
        try:
            from backends.tenancy.models import StudyMembership, StudySite
            
            membership = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            ).first()
            
            if not membership:
                sites = []
            elif membership.can_access_all_sites:
                sites = list(
                    StudySite.objects.filter(study=study)
                    .values_list('site__code', flat=True)
                    .distinct()
                )
            else:
                sites = list(
                    membership.study_sites
                    .values_list('site__code', flat=True)
                    .distinct()
                )
            
            cache.set(cache_key, sites, cls.CACHE_TTL)
            
        except Exception as e:
            logger.error(f"Error getting sites: {type(e).__name__}")
            sites = []
        
        return sites
    
    @classmethod
    def user_has_site_access(cls, user, study, site_code: str) -> bool:
        """Check if user has access to a specific site."""
        return site_code in cls.get_user_sites(user, study)
    
    # =========================================================================
    # Study Access Tracking
    # =========================================================================
    
    @classmethod
    def track_study_access(cls, user, study) -> None:
        """
        Track study access (throttled to reduce DB writes).
        
        Only updates every 5 minutes per user/study combination.
        """
        cache_key = cls._cache_key('access', user.pk, study.pk)
        
        if cache.get(cache_key):
            return  # Already tracked recently
        
        try:
            from backends.tenancy.models import User
            
            User.objects.filter(pk=user.pk).update(
                last_study_accessed_id=study.pk,
                last_study_accessed_at=timezone.now()
            )
            
            cache.set(cache_key, True, 300)  # 5 minutes
            
        except Exception as e:
            logger.debug(f"Error tracking access: {type(e).__name__}")
    
    # =========================================================================
    # User Studies
    # =========================================================================
    
    @classmethod
    def get_user_studies(cls, user) -> List:
        """Get all accessible studies for a user."""
        if not user:
            return []
        
        cache_key = cls._cache_key('studies', user.pk)
        study_ids = cache.get(cache_key)
        
        if study_ids is None:
            try:
                from backends.tenancy.models import Study
                
                study_ids = list(
                    Study.objects.filter(
                        memberships__user=user,
                        memberships__is_active=True,
                        status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
                    ).values_list('id', flat=True).distinct()
                )
                
                cache.set(cache_key, study_ids, cls.CACHE_TTL)
                
            except Exception as e:
                logger.error(f"Error getting user studies: {type(e).__name__}")
                return []
        
        if study_ids:
            from backends.tenancy.models import Study
            return list(Study.objects.filter(id__in=study_ids).order_by('code'))
        
        return []
    
    # =========================================================================
    # Cache Management
    # =========================================================================
    
    @classmethod
    def clear_user_cache(cls, user) -> None:
        """Clear all cache for a user."""
        if not user:
            return
        
        # Clear known cache keys
        patterns = ['perms', 'sites', 'studies', 'access']
        
        try:
            from backends.tenancy.models import Study
            
            # Get user's studies
            study_ids = Study.objects.filter(
                memberships__user=user
            ).values_list('id', flat=True)
            
            keys_to_delete = [cls._cache_key('studies', user.pk)]
            
            for study_id in study_ids:
                for pattern in patterns:
                    keys_to_delete.append(cls._cache_key(pattern, user.pk, study_id))
            
            cache.delete_many(keys_to_delete)
            
        except Exception:
            pass
    
    @classmethod
    def clear_study_cache(cls, study) -> None:
        """Clear all cache for a study."""
        if not study:
            return
        
        try:
            from backends.tenancy.models import StudyMembership
            
            user_ids = StudyMembership.objects.filter(
                study=study
            ).values_list('user_id', flat=True)
            
            keys_to_delete = []
            for user_id in user_ids:
                for pattern in ['perms', 'sites', 'access']:
                    keys_to_delete.append(cls._cache_key(pattern, user_id, study.pk))
            
            if keys_to_delete:
                cache.delete_many(keys_to_delete)
                
        except Exception:
            pass
    
    # =========================================================================
    # Group Sync
    # =========================================================================
    
    @classmethod
    def sync_user_groups(cls, user) -> Dict[str, int]:
        """Sync user's Django groups with study memberships."""
        if not user:
            return {'added': 0, 'removed': 0}
        
        try:
            from backends.tenancy.models import StudyMembership
            from django.contrib.auth.models import Group
            
            # Get expected groups from active memberships
            memberships = StudyMembership.objects.filter(
                user=user, is_active=True
            ).select_related('group')
            
            expected = {m.group for m in memberships if m.group}
            
            # Get current study groups
            current = set(user.groups.filter(name__startswith='Study '))
            
            # Calculate diff
            to_add = expected - current
            to_remove = current - expected
            
            # Apply changes
            if to_add:
                user.groups.add(*to_add)
            if to_remove:
                user.groups.remove(*to_remove)
            
            if to_add or to_remove:
                cls.clear_user_cache(user)
            
            return {'added': len(to_add), 'removed': len(to_remove)}
            
        except Exception as e:
            logger.error(f"Error syncing groups: {type(e).__name__}")
            return {'added': 0, 'removed': 0}


# =============================================================================
# Validators
# =============================================================================

def validate_study_code(value: str) -> None:
    """Validate study code format."""
    if not value:
        raise ValidationError("Study code is required")
    
    if not re.match(r'^[A-Z][A-Z0-9_]*$', value):
        raise ValidationError(
            "Study code must start with a letter and contain only "
            "uppercase letters, numbers, and underscores"
        )
    
    if len(value) < 3 or len(value) > 20:
        raise ValidationError("Study code must be between 3 and 20 characters")
    
    reserved = {'ADMIN', 'SYSTEM', 'DEFAULT', 'PUBLIC', 'MANAGEMENT'}
    if value in reserved:
        raise ValidationError(f"'{value}' is a reserved code")


def validate_database_name(value: str) -> None:
    """Validate database name format."""
    if not value:
        raise ValidationError("Database name is required")
    
    prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
    if not value.startswith(prefix):
        raise ValidationError(f"Database name must start with '{prefix}'")
    
    if not re.match(r'^[a-z][a-z0-9_]*$', value):
        raise ValidationError("Database name contains invalid characters")
    
    if len(value) > 63:
        raise ValidationError("Database name too long (max 63)")


def validate_site_code(value: str) -> None:
    """Validate site code format."""
    if not value:
        raise ValidationError("Site code is required")
    
    if not re.match(r'^[A-Z0-9_]{2,10}$', value):
        raise ValidationError("Site code must be 2-10 uppercase alphanumeric characters")


# =============================================================================
# Permission Helpers
# =============================================================================

def get_model_permissions(app_label: str, model_name: str) -> List[Permission]:
    """Get all permissions for a model."""
    try:
        content_type = ContentType.objects.get(
            app_label=app_label,
            model=model_name.lower()
        )
        return list(Permission.objects.filter(content_type=content_type))
    except ContentType.DoesNotExist:
        return []


def get_all_study_permissions(study_code: str) -> List[Permission]:
    """Get all permissions for a study."""
    app_label = f'study_{study_code.lower()}'
    return list(Permission.objects.filter(content_type__app_label=app_label))