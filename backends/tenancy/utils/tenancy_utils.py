# backend/tenancy/utils/tenancy_utils.py - COMPLETE OPTIMIZED VERSION
"""
Optimized utility functions for tenancy operations
Uses Django's default permission system with triple-layer caching
"""
from collections import OrderedDict
from typing import Set, List, Dict, Any, Optional
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from datetime import datetime
import hashlib
import re
import time
import logging

logger = logging.getLogger(__name__)


# ==========================================
# OPTIMIZED UTILITY CLASS
# ==========================================

class TenancyUtils:
    """
    OPTIMIZED: Centralized utility functions with triple-layer caching
    
    Layer 1: Request cache (in-memory, fastest, cleared per request)
    Layer 2: Django cache (Redis/Memcached, fast, persistent)
    Layer 3: Database (slowest, only when cache misses)
    """
    
    CACHE_TTL = 300  # 5 minutes
    
    # Request-level cache (cleared periodically)
    _MAX_CACHE_SIZE = 1000  # Maximum number of cached items
    _request_cache: OrderedDict = OrderedDict()
    _cache_timestamp: Optional[float] = None
    _CACHE_CLEAR_INTERVAL = 60  # Clear every 60 seconds
    
    # ==========================================
    # REQUEST-LEVEL CACHE MANAGEMENT
    # ==========================================
    
    @classmethod
    def _get_request_cache(cls, key: str) -> Optional[Any]:
        """
        Fast in-memory cache with automatic cleanup
        """
        now = time.time()
        
        # Clear cache if too old or too large
        if cls._cache_timestamp:
            should_clear = (
                (now - cls._cache_timestamp) > cls._CACHE_CLEAR_INTERVAL or
                len(cls._request_cache) > cls._MAX_CACHE_SIZE * 1.5  # Emergency clear at 150%
            )
            if should_clear:
                cls._clear_old_cache_entries()
                cls._cache_timestamp = now
        else:
            cls._cache_timestamp = now
        
        # Move to end for LRU behavior
        if key in cls._request_cache:
            cls._request_cache.move_to_end(key)
            return cls._request_cache[key]
        
        return None
    
    @classmethod
    def _set_request_cache(cls, key: str, value: Any):
        """
        Set request-level cache with LRU eviction
        """
        if cls._cache_timestamp is None:
            cls._cache_timestamp = time.time()
        
        # Check size limit
        if len(cls._request_cache) >= cls._MAX_CACHE_SIZE:
            # Remove oldest item (LRU)
            cls._request_cache.popitem(last=False)
            logger.debug(f"Request cache evicted oldest item (size: {len(cls._request_cache)})")
        
        # Add new item
        cls._request_cache[key] = value
        cls._request_cache.move_to_end(key)

    @classmethod
    def _clear_old_cache_entries(cls):
        """
        Clear old cache entries to prevent memory leak
        Keep only the most recent half of entries
        """
        if len(cls._request_cache) > cls._MAX_CACHE_SIZE // 2:
            # Keep only the most recent half
            items_to_remove = len(cls._request_cache) - (cls._MAX_CACHE_SIZE // 2)
            for _ in range(items_to_remove):
                cls._request_cache.popitem(last=False)
            
            logger.debug(f"Cleared {items_to_remove} old cache entries")

    @classmethod
    def get_cache_statistics(cls) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring
        """
        return {
            'request_cache_size': len(cls._request_cache),
            'request_cache_max_size': cls._MAX_CACHE_SIZE,
            'cache_timestamp': cls._cache_timestamp,
            'cache_ttl': cls.CACHE_TTL,
            'clear_interval': cls._CACHE_CLEAR_INTERVAL,
            'memory_usage_estimate': cls._estimate_cache_memory(),}
    
    @classmethod
    def _estimate_cache_memory(cls) -> str:
        """
        Estimate memory usage of cache
        """
        import sys
        
        total_size = sys.getsizeof(cls._request_cache)
        for key, value in cls._request_cache.items():
            total_size += sys.getsizeof(key) + sys.getsizeof(value)
        
        # Convert to human readable
        if total_size < 1024:
            return f"{total_size} B"
        elif total_size < 1024 * 1024:
            return f"{total_size / 1024:.2f} KB"
        else:
            return f"{total_size / (1024 * 1024):.2f} MB"
    
    @classmethod
    def clear_request_cache(cls):
        """
        Manually clear request cache
        """
        cls._request_cache.clear()
        cls._cache_timestamp = None
        logger.debug("Request cache manually cleared")
    
    @classmethod
    def get_cache_key(cls, prefix: str, *args) -> str:
        """
        Generate consistent cache key
        
        Args:
            prefix: Key prefix (e.g., 'perms', 'sites')
            *args: Additional arguments for key
            
        Returns:
            Cache key string
        """
        key_parts = [str(arg) for arg in args]
        key_string = "_".join(key_parts)
        
        # Hash if too long (cache key limits)
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}_{key_hash}"
        
        return f"{prefix}_{key_string}"
    
    # ==========================================
    # PERMISSION MANAGEMENT (Django Default)
    # ==========================================
    
    @classmethod
    def get_user_permissions(cls, user, study) -> Set[str]:
        """
        OPTIMIZED: Get user permissions for a study using Django's default system
        Triple-layer caching for maximum performance
        
        Args:
            user: User instance
            study: Study instance
            
        Returns:
            Set of permission codenames (e.g., {'add_patient', 'view_patient'})
        """
        # Layer 1: Request cache (fastest)
        req_key = f"req_perms_{user.pk}_{study.pk}"
        permissions = cls._get_request_cache(req_key)
        if permissions is not None:
            return permissions
        
        # Layer 2: Django cache (fast)
        cache_key = cls.get_cache_key("perms", user.pk, study.pk)
        permissions = cache.get(cache_key)
        
        if permissions is None:
            # Layer 3: Database query (slowest)
            try:
                from backends.tenancy.models import StudyMembership
                
                permissions = set()
                
                # Get study app label
                study_code_lower = study.code.lower()
                app_label = f'study_{study_code_lower}'
                
                # Optimized query with select_related and prefetch_related
                memberships = StudyMembership.objects.filter(
                    user=user,
                    study=study,
                    is_active=True
                ).select_related('group').prefetch_related(
                    Prefetch(
                        'group__permissions',
                        queryset=Permission.objects.filter(
                            content_type__app_label=app_label
                        ).select_related('content_type')
                    )
                )
                
                # Collect all permissions from groups (filtered by app)
                for membership in memberships:
                    for perm in membership.group.permissions.all():
                        if perm.content_type.app_label == app_label:
                            permissions.add(perm.codename)
                
                # Cache in Django cache
                cache.set(cache_key, permissions, cls.CACHE_TTL)
                logger.debug(
                    f"Cached permissions for user {user.pk} in study {study.pk}: "
                    f"{len(permissions)} perms"
                )
                
            except Exception as e:
                logger.error(f"Error getting permissions: {e}", exc_info=True)
                permissions = set()
        
        # Store in request cache
        cls._set_request_cache(req_key, permissions)
        return permissions
    
    @classmethod
    def user_has_permission(cls, user, study, permission_codename: str) -> bool:
        """
        Check if user has a specific permission in a study
        
        Args:
            user: User instance
            study: Study instance
            permission_codename: Permission codename (e.g., 'add_patient')
            
        Returns:
            True if user has permission
        """
        permissions = cls.get_user_permissions(user, study)
        return permission_codename in permissions
    
    @classmethod
    def get_permission_display(cls, user, study) -> Dict[str, List[str]]:
        """
        Get organized permission display for user in study
        
        Returns:
            Dict grouping permissions by model
        """
        permissions = cls.get_user_permissions(user, study)
        
        # Group by model
        grouped = {}
        for perm in permissions:
            parts = perm.split('_', 1)
            if len(parts) == 2:
                action, model = parts
                if model not in grouped:
                    grouped[model] = []
                grouped[model].append(action)
        
        return grouped
    
    # ==========================================
    # SITE ACCESS MANAGEMENT
    # ==========================================
    
    @classmethod
    def get_user_sites(cls, user, study) -> List[str]:
        """
        OPTIMIZED: Get sites user can access in a study
        Triple-layer caching
        
        Args:
            user: User instance
            study: Study instance
            
        Returns:
            List of site codes
        """
        # Layer 1: Request cache
        req_key = f"req_sites_{user.pk}_{study.pk}"
        sites = cls._get_request_cache(req_key)
        if sites is not None:
            return sites
        
        # Layer 2: Django cache
        cache_key = cls.get_cache_key("sites", user.pk, study.pk)
        sites = cache.get(cache_key)
        
        if sites is None:
            # Layer 3: Database with optimized query
            try:
                from backends.tenancy.models import StudyMembership, StudySite
                
                # Single efficient query
                membership = StudyMembership.objects.filter(
                    user=user,
                    study=study,
                    is_active=True
                ).select_related('study').prefetch_related(
                    Prefetch(
                        'study_sites',
                        queryset=StudySite.objects.select_related('site')
                    )
                ).first()
                
                if not membership:
                    sites = []
                elif membership.can_access_all_sites:
                    # Get all sites for study
                    sites = list(
                        StudySite.objects.filter(study=study)
                        .select_related('site')
                        .values_list('site__code', flat=True)
                        .distinct()
                    )
                else:
                    # Get assigned sites only
                    sites = list(
                        membership.study_sites
                        .values_list('site__code', flat=True)
                        .distinct()
                    )
                
                # Cache in Django cache
                cache.set(cache_key, sites, cls.CACHE_TTL)
                logger.debug(
                    f"Cached sites for user {user.pk} in study {study.pk}: "
                    f"{len(sites)} sites"
                )
                
            except Exception as e:
                logger.error(f"Error getting sites: {e}", exc_info=True)
                sites = []
        
        # Store in request cache
        cls._set_request_cache(req_key, sites)
        return sites
    
    @classmethod
    def user_has_site_access(cls, user, study, site_code: str) -> bool:
        """
        Check if user has access to a specific site
        
        Args:
            user: User instance
            study: Study instance
            site_code: Site code to check
            
        Returns:
            True if user has access
        """
        sites = cls.get_user_sites(user, study)
        return site_code in sites
    
    # ==========================================
    # STUDY ACCESS TRACKING
    # ==========================================
    
    @classmethod
    def track_study_access(cls, user, study) -> None:
        """
        OPTIMIZED: Throttled study access tracking
        Only updates database every 5 minutes to reduce writes
        
         FIXED: Use correct field names (last_study_accessed_id)
        
        Args:
            user: User instance
            study: Study instance
        """
        from backends.tenancy.models.user import User
        
        cache_key = cls.get_cache_key("last_access", user.pk, study.pk)
        last_tracked = cache.get(cache_key)
        
        now = timezone.now()
        should_update = True
        
        if last_tracked:
            # Parse timestamp if string
            if isinstance(last_tracked, str):
                try:
                    last_tracked = datetime.fromisoformat(last_tracked)
                except:
                    last_tracked = None
            
            # Check if enough time passed
            if last_tracked:
                delta = now - last_tracked
                should_update = delta.total_seconds() > 300  # 5 minutes
        
        if should_update:
            try:
                #  FIXED: Sử dụng field _id để lưu ID của study
                User.objects.filter(pk=user.pk).update(
                    last_study_accessed_id=study.pk,  #  Đúng field name
                    last_study_accessed_at=now
                )
                
                # Cache for next check
                cache.set(cache_key, now.isoformat(), 300)
                logger.debug(f"Updated study access: user {user.pk} -> study {study.code}")
                
            except Exception as e:
                logger.error(f"Error tracking study access: {e}", exc_info=True)
    
    # ==========================================
    # USER STUDY MANAGEMENT
    # ==========================================
    
    @classmethod
    def get_user_studies(cls, user) -> List:
        """
        OPTIMIZED: Get all accessible studies for a user
        With request-level caching
        
        Args:
            user: User instance
            
        Returns:
            List of Study instances
        """
        # Check request cache
        req_key = f"req_user_studies_{user.pk}"
        study_ids = cls._get_request_cache(req_key)
        
        if study_ids is None:
            # Check Django cache
            cache_key = cls.get_cache_key("user_studies", user.pk)
            study_ids = cache.get(cache_key)
            
            if study_ids is None:
                # Database query
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
                    logger.error(f"Error getting user studies: {e}")
                    study_ids = []
            
            # Store in request cache
            cls._set_request_cache(req_key, study_ids)
        
        # Fetch full objects if needed
        if study_ids:
            from backends.tenancy.models import Study
            studies = Study.objects.filter(
                id__in=study_ids
            ).select_related('created_by').order_by('code')
            return list(studies)
        
        return []
    
    @classmethod
    def get_user_study_count(cls, user) -> int:
        """
        Get count of accessible studies for user
        
        Args:
            user: User instance
            
        Returns:
            Number of accessible studies
        """
        studies = cls.get_user_studies(user)
        return len(studies)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    
    @classmethod
    def bulk_get_permissions(cls, user, study_ids: List[int]) -> Dict[int, Set[str]]:
        """
        OPTIMIZED: Bulk permission fetching with single query
        
        Args:
            user: User instance
            study_ids: List of study IDs
            
        Returns:
            Dict mapping study_id to set of permission codenames
        """
        result = {}
        uncached_ids = []
        
        # Check cache for each study
        for study_id in study_ids:
            cache_key = cls.get_cache_key("perms", user.pk, study_id)
            perms = cache.get(cache_key)
            if perms is not None:
                result[study_id] = perms
            else:
                uncached_ids.append(study_id)
        
        # Bulk fetch uncached
        if uncached_ids:
            try:
                from backends.tenancy.models import StudyMembership, Study
                
                # Get study codes for app labels
                studies = Study.objects.filter(id__in=uncached_ids)
                study_app_labels = {
                    s.pk: f'study_{s.code.lower()}' for s in studies
                }
                
                # Single optimized query
                memberships = StudyMembership.objects.filter(
                    user=user,
                    study_id__in=uncached_ids,
                    is_active=True
                ).select_related('group', 'study').prefetch_related('group__permissions__content_type')
                
                # Group by study
                study_perms = {}
                for membership in memberships:
                    study_id = membership.study.pk
                    app_label = study_app_labels.get(study_id)
                    
                    if study_id not in study_perms:
                        study_perms[study_id] = set()
                    
                    # Add permissions for this study's app only
                    for perm in membership.group.permissions.all():
                        if perm.content_type.app_label == app_label:
                            study_perms[study_id].add(perm.codename)
                
                # Cache and add to result
                for study_id in uncached_ids:
                    perms = study_perms.get(study_id, set())
                    cache_key = cls.get_cache_key("perms", user.pk, study_id)
                    cache.set(cache_key, perms, cls.CACHE_TTL)
                    result[study_id] = perms
                    
            except Exception as e:
                logger.error(f"Error bulk fetching permissions: {e}")
        
        return result
    
    # ==========================================
    # CACHE MANAGEMENT
    # ==========================================
    
    @classmethod
    def clear_user_cache(cls, user) -> int:
        """
        OPTIMIZED: Bulk cache clearing with pattern support
        
        Args:
            user: User instance
            
        Returns:
            Number of cache keys cleared
        """
        # Clear request cache
        cls._request_cache.clear()
        
        # Specific keys to clear
        specific_keys = []
        
        # Build list of specific keys
        try:
            from backends.tenancy.models import Study
            study_ids = Study.objects.filter(
                memberships__user=user
            ).values_list('id', flat=True)
            
            for study_id in study_ids:
                specific_keys.extend([
                    cls.get_cache_key("perms", user.pk, study_id),
                    cls.get_cache_key("sites", user.pk, study_id),
                    cls.get_cache_key("last_access", user.pk, study_id),
                ])
            
            specific_keys.append(cls.get_cache_key("user_studies", user.pk))
            
        except Exception as e:
            logger.error(f"Error building cache keys: {e}")
        
        # Additional general keys
        specific_keys.extend([
            f"user_obj_{user.pk}",
            f"user_blocked_{user.username}",
            f"mw_study_*_{user.pk}",
        ])
        
        cleared = 0
        
        # Bulk delete for non-pattern keys
        non_pattern_keys = [k for k in specific_keys if '*' not in k]
        if non_pattern_keys:
            cache.delete_many(non_pattern_keys)
            cleared += len(non_pattern_keys)
        
        # Pattern-based deletion (Redis only)
        if hasattr(cache, 'delete_pattern'):
            delete_pattern = getattr(cache, 'delete_pattern')
            patterns = ['perms_*', 'sites_*', 'user_studies_*', 'last_access_*', 'mw_*']
            for pattern in patterns:
                try:

                    cleared += delete_pattern(pattern)
                except Exception as e:
                    logger.error(f"Error clearing pattern {pattern}: {e}")
        
        logger.debug(f"Cleared {cleared} cache keys for user {user.pk}")
        return cleared
    
    @classmethod
    def clear_study_cache(cls, study) -> int:
        """
        OPTIMIZED: Bulk study cache clearing
        
        Args:
            study: Study instance
            
        Returns:
            Number of cache keys cleared
        """
        cls._request_cache.clear()
        
        specific_keys = [
            f"study_stats_{study.pk}",
            f"db_config_{study.db_name}",
        ]
        
        cache.delete_many(specific_keys)
        cleared = len(specific_keys)
        
        # Pattern-based deletion
        if hasattr(cache, 'delete_pattern'):
            patterns = [
                f"*_{study.pk}",
                f"study_{study.pk}_*",
                f"mw_study_{study.pk}_*",
                f"perms_*_{study.pk}",
                f"sites_*_{study.pk}",
            ]
            delete_pattern = getattr(cache, 'delete_pattern')
            for pattern in patterns:
                try:
                    cleared += delete_pattern(pattern)
                except Exception as e:
                    logger.error(f"Error deleting pattern {pattern}: {e}")
        
        logger.debug(f"Cleared {cleared} cache keys for study {study.pk}")
        return cleared
    
    @classmethod
    def clear_all_cache(cls) -> int:
        """
        Clear all tenancy-related cache
        
        Returns:
            Number of cache keys cleared (approximate)
        """
        cls._request_cache.clear()
        
        cleared = 0
        
        if hasattr(cache, 'delete_pattern'):
            patterns = ['perms_*', 'sites_*', 'user_studies_*', 'last_access_*', 'mw_*']
            delete_pattern = getattr(cache, 'delete_pattern')
            for pattern in patterns:
                try:
                    cleared += delete_pattern(pattern)
                except Exception as e:
                    logger.error(f"Error clearing pattern {pattern}: {e}")
        else:
            # Fallback: clear entire cache (not recommended in production)
            logger.warning("Cache backend doesn't support pattern deletion")
            cache.clear()
            cleared = 1
        
        logger.debug(f"Cleared approximately {cleared} cache keys")
        return cleared
    
    # ==========================================
    # STATISTICS & MONITORING
    # ==========================================
    
    @classmethod
    def get_study_stats(cls, study) -> Dict[str, Any]:
        """
        OPTIMIZED: Study statistics with short cache TTL
        
        Args:
            study: Study instance
            
        Returns:
            Dict with study statistics
        """
        cache_key = cls.get_cache_key("study_stats", study.pk)
        stats = cache.get(cache_key)
        
        if stats is None:
            try:
                from backends.tenancy.models import StudyMembership, StudySite
                
                stats = {
                    'id': study.pk,
                    'code': study.code,
                    'name': study.safe_translation_getter('name', any_language=True),
                    'status': study.status,
                    'created_at': study.created_at.isoformat() if study.created_at else None,
                    'user_count': StudyMembership.objects.filter(
                        study=study,
                        is_active=True
                    ).count(),
                    'site_count': StudySite.objects.filter(study=study).count(),
                    'db_name': study.db_name,
                }
                
                # Cache for 1 minute only (stats change frequently)
                cache.set(cache_key, stats, 60)
                
            except Exception as e:
                logger.error(f"Error getting study stats: {e}")
                stats = {'error': str(e)}
        
        return stats
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache statistics
        """
        return {
            'request_cache_size': len(cls._request_cache),
            'request_cache_timestamp': cls._cache_timestamp,
            'cache_ttl': cls.CACHE_TTL,
            'clear_interval': cls._CACHE_CLEAR_INTERVAL,
        }
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    @classmethod
    def validate_study_code(cls, code: str) -> bool:
        """Validate study code format"""
        return bool(re.match(r'^[A-Z0-9_]+$', code) and 3 <= len(code) <= 20)
    
    @classmethod
    def validate_site_code(cls, code: str) -> bool:
        """Validate site code format"""
        return bool(re.match(r'^[A-Z0-9_]+$', code) and 2 <= len(code) <= 10)
    
    @classmethod
    def generate_db_name(cls, study_code: str) -> str:
        """Generate database name from study code"""
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        return f"{prefix}{study_code.lower()}"
    
    @classmethod
    def parse_permission_code(cls, perm_code: str) -> tuple:
        """
        Parse permission code into action and model
        
        Args:
            perm_code: e.g., 'add_patient'
            
        Returns:
            Tuple of (action, model) e.g., ('add', 'patient')
        """
        parts = perm_code.split('_', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return perm_code, ''
    
    @classmethod
    def sync_user_groups(cls, user) -> Dict[str, int]:
        """
        Sync user's Django groups based on active memberships
        
        Returns:
            Dict with sync statistics
        """
        from backends.tenancy.models import StudyMembership
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        try:
            # Get active memberships
            memberships = StudyMembership.objects.filter(
                user=user,
                is_active=True
            ).select_related('group')
            
            # Groups user should have
            should_have = set(m.group for m in memberships if m.group)
            
            # Current study groups
            current = set()
            for group in user.groups.all():
                if StudyRoleManager.is_study_group(group.name):
                    current.add(group)
            
            # Calculate changes
            to_add = should_have - current
            to_remove = current - should_have
            
            # Apply changes
            for group in to_add:
                user.groups.add(group)
            
            for group in to_remove:
                user.groups.remove(group)
            
            # Clear cache
            cls.clear_user_cache(user)
            
            return {
                'added': len(to_add),
                'removed': len(to_remove),
                'total': len(should_have)
            }
            
        except Exception as e:
            logger.error(f"Error syncing groups for {user.username}: {e}")
            return {'added': 0, 'removed': 0, 'total': 0}


# ==========================================
# VALIDATORS (Django Form/Model Validators)
# ==========================================

def validate_study_code(value: str) -> None:
    """Validate study code format for Django forms/models"""
    if not value:
        raise ValidationError("Study code is required")
    
    if not re.match(r'^[A-Z][A-Z0-9_]*$', value):
        raise ValidationError(
            "Study code must start with a letter and contain only "
            "uppercase letters, numbers, and underscores"
        )
    
    if len(value) < 3 or len(value) > 20:
        raise ValidationError("Study code must be between 3 and 20 characters")
    
    reserved_words = ['ADMIN', 'SYSTEM', 'DEFAULT', 'PUBLIC', 'MANAGEMENT', 'DATA']
    if value in reserved_words:
        raise ValidationError(f"'{value}' is a reserved study code")


def validate_database_name(value: str) -> None:
    """Validate database name format"""
    if not value:
        raise ValidationError("Database name is required")
    
    prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
    
    if not value.startswith(prefix):
        raise ValidationError(f"Database name must start with '{prefix}'")
    
    if not re.match(r'^[a-z][a-z0-9_]*$', value):
        raise ValidationError(
            "Database name must start with lowercase letter and contain only "
            "lowercase letters, numbers, and underscores"
        )
    
    if len(value) > 63:
        raise ValidationError("Database name cannot exceed 63 characters")


def validate_site_code(value: str) -> None:
    """Validate site code format"""
    if not value:
        raise ValidationError("Site code is required")
    
    if not re.match(r'^[A-Z][A-Z0-9_]*$', value):
        raise ValidationError(
            "Site code must start with a letter and contain only "
            "uppercase letters, numbers, and underscores"
        )
    
    if len(value) < 2 or len(value) > 10:
        raise ValidationError("Site code must be between 2 and 10 characters")


def validate_username(value: str) -> None:
    """Validate username format"""
    if not value:
        raise ValidationError("Username is required")
    
    if not re.match(r'^[a-zA-Z0-9._-]+$', value):
        raise ValidationError(
            "Username can only contain letters, numbers, "
            "dots, hyphens, and underscores"
        )
    
    if len(value) < 3 or len(value) > 30:
        raise ValidationError("Username must be between 3 and 30 characters")
    
    reserved_usernames = [
        'admin', 'root', 'system', 'administrator',
        'superuser', 'user', 'test', 'demo'
    ]
    if value.lower() in reserved_usernames:
        raise ValidationError(f"'{value}' is a reserved username")


def validate_email(value: str) -> None:
    """Validate email format with additional checks"""
    from django.core.validators import validate_email as django_validate_email
    
    if not value:
        raise ValidationError("Email is required")
    
    try:
        django_validate_email(value)
    except ValidationError:
        raise ValidationError("Enter a valid email address")
    
    if '..' in value:
        raise ValidationError("Email cannot contain consecutive dots")
    
    # Optional: Block disposable emails
    disposable_domains = [
        'tempmail.com', 'throwaway.email', '10minutemail.com',
        'guerrillamail.com', 'mailinator.com'
    ]
    domain = value.split('@')[-1].lower()
    if domain in disposable_domains:
        raise ValidationError("Disposable email addresses are not allowed")


def validate_permission_code(value: str) -> None:
    """Validate Django permission code format"""
    if not value:
        raise ValidationError("Permission code is required")
    
    # Django permission format: action_model (e.g., add_patient, view_visit)
    if not re.match(r'^[a-z]+_[a-z]+$', value):
        raise ValidationError(
            "Permission code must be in format 'action_model' "
            "(lowercase letters only, e.g., 'add_patient')"
        )


def validate_schema_name(value: str) -> None:
    """Validate PostgreSQL schema name"""
    if not value:
        raise ValidationError("Schema name is required")
    
    if not re.match(r'^[a-z][a-z0-9_]*$', value):
        raise ValidationError(
            "Schema name must start with lowercase letter and contain only "
            "lowercase letters, numbers, and underscores"
        )
    
    reserved_schemas = ['pg_catalog', 'information_schema', 'pg_toast', 'pg_temp']
    if value in reserved_schemas:
        raise ValidationError(f"'{value}' is a reserved schema name")
    
    if len(value) > 63:
        raise ValidationError("Schema name cannot exceed 63 characters")


# ==========================================
# PERMISSION HELPER FUNCTIONS
# ==========================================

def get_model_permissions(app_label: str, model_name: str) -> List[Permission]:
    """
    Get all Django permissions for a specific model
    
    Args:
        app_label: App label (e.g., 'study_43en')
        model_name: Model name (e.g., 'patient')
        
    Returns:
        List of Permission objects
    """
    try:
        content_type = ContentType.objects.get(
            app_label=app_label,
            model=model_name.lower()
        )
        return list(Permission.objects.filter(content_type=content_type))
    except ContentType.DoesNotExist:
        logger.warning(f"ContentType not found: {app_label}.{model_name}")
        return []


def get_all_study_permissions(study_code: str) -> List[Permission]:
    """
    Get all permissions for a study
    
    Args:
        study_code: Study code (e.g., '43EN')
        
    Returns:
        List of Permission objects
    """
    app_label = f'study_{study_code.lower()}'
    return list(Permission.objects.filter(content_type__app_label=app_label))


def create_custom_permission(app_label: str, codename: str, name: str) -> Optional[Permission]:
    """
    Create a custom permission (beyond Django's default add/change/delete/view)
    
    Args:
        app_label: App label (e.g., 'study_43en')
        codename: Permission codename (e.g., 'export_patient')
        name: Human-readable name (e.g., 'Can export patient data')
        
    Returns:
        Permission object or None if failed
    """
    try:
        # Get or create a content type for the app
        content_type, _ = ContentType.objects.get_or_create(
            app_label=app_label,
            model='_app'  # Special marker for app-level permissions
        )
        
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )
        
        if created:
            logger.debug(f"Created custom permission: {app_label}.{codename}")
        
        return permission
        
    except Exception as e:
        logger.error(f"Error creating custom permission: {e}")
        return None