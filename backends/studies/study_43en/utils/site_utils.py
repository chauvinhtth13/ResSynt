# File: backends/studies/study_43en/utils/site_utils.py

"""
Site Filtering Utilities for Views
===================================

High-level helper functions matching dashboard.py logic
OPTIMIZED: Redis caching integrated
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
import logging
import hashlib

logger = logging.getLogger(__name__)

DB_ALIAS = 'db_study_43en'

# 🚀 Cache timeout configuration
CACHE_TIMEOUT_SHORT = 300  # 5 minutes - cho query results
CACHE_TIMEOUT_MEDIUM = 1800  # 30 minutes - cho metadata
CACHE_TIMEOUT_LONG = 3600  # 1 hour - cho rarely changed data


def get_site_filter_params(request):
    """
    REFACTORED: Single source of truth - uses middleware context
    
    Determine site filter strategy from UnifiedTenancyMiddleware context.
    Middleware ALWAYS injects site context for Study 43EN.
    
    Returns:
        tuple: (site_filter, filter_type)
            - site_filter: 'all' | str | list
            - filter_type: 'all' | 'single' | 'multiple'
    
    Priority Order:
        1. Single site selected → filter by that site only
        2. can_access_all_sites=True → no site filtering (see ALL)
        3. Multiple sites assigned → filter by user's sites
        4. Fallback → empty (no access)
    """
    # Get from UnifiedTenancyMiddleware context
    selected_site_id = getattr(request, 'selected_site_id', 'all')
    can_access_all = getattr(request, 'can_access_all_sites', False)
    user_sites = getattr(request, 'user_sites', None)
    
    # Handle SimpleLazyObject - force evaluation if needed
    if hasattr(user_sites, '__iter__') and not isinstance(user_sites, (str, list)):
        user_sites = list(user_sites) if user_sites else []
    elif user_sites is None:
        user_sites = []
    else:
        user_sites = list(user_sites)
    
    # Log current context for debugging
    logger.debug(
        f"Site filter context: selected={selected_site_id}, "
        f"can_access_all={can_access_all}, user_sites={user_sites}"
    )
    
    # Strategy 1: Single site selected by user
    if selected_site_id and selected_site_id != 'all':
        logger.info(f"Site filter: single site '{selected_site_id}'")
        return (selected_site_id, 'single')
    
    # Strategy 2: User has can_access_all_sites=True → see ALL data
    if can_access_all:
        logger.info(f"Site filter: ALL (can_access_all_sites=True)")
        return ('all', 'all')
    
    # Strategy 3: User has specific sites assigned
    if user_sites:
        logger.info(f"Site filter: multiple sites {user_sites}")
        return (user_sites, 'multiple')
    
    # Strategy 4: No site access - return empty
    logger.warning(f"Site filter: NO ACCESS (no sites assigned, can_access_all=False)")
    return ([], 'multiple')


def get_filtered_queryset(model, site_filter, filter_type, use_cache=True):
    """
    🚀 OPTIMIZED: Get filtered queryset với Redis caching
    
    Args:
        model: Django model class
        site_filter: 'all' | str | list
        filter_type: 'all' | 'single' | 'multiple'
        use_cache: Enable/disable caching (default True)
    
    Returns:
        Filtered QuerySet using db_study_43en
    """
    # 🔥 Cache key generation
    if use_cache:
        cache_key = _generate_cache_key('queryset', model.__name__, site_filter, filter_type)
        
        # Try to get from cache
        cached_pks = cache.get(cache_key)
        if cached_pks is not None:
            logger.debug(f"Cache HIT: [{model.__name__}] {len(cached_pks)} objects")
            # Return queryset filtered by cached PKs
            return model.objects.using(DB_ALIAS).filter(pk__in=cached_pks)
    
    # Cache MISS - query database
    if filter_type == 'all':
        logger.debug(f"[{model.__name__}] Query all sites")
        queryset = model.objects.using(DB_ALIAS)
    
    elif filter_type == 'multiple':
        logger.debug(f"[{model.__name__}] Query multiple sites: {site_filter}")
        
        if not site_filter:
            logger.warning(f"[{model.__name__}] Empty site filter - returning empty")
            return model.objects.using(DB_ALIAS).none()
        
        # Use manager's filter_by_site which handles multiple sites
        queryset = model.site_objects.using(DB_ALIAS).filter_by_site(site_filter)
    
    else:  # filter_type == 'single'
        logger.debug(f"[{model.__name__}] Query single site: {site_filter}")
        queryset = model.site_objects.using(DB_ALIAS).filter_by_site(site_filter)
    
    # 🔥 Cache the result (PKs only to save memory)
    if use_cache:
        try:
            pks = list(queryset.values_list('pk', flat=True))
            cache.set(cache_key, pks, CACHE_TIMEOUT_SHORT)
            logger.debug(f"Cached: [{model.__name__}] {len(pks)} objects")
        except Exception as e:
            logger.warning(f"Failed to cache queryset: {e}")
    
    return queryset


def _generate_cache_key(*args):
    """
    Generate unique cache key from arguments
    
    Example: 'site_query_SCR_CASE_all_all_v1'
    """
    # Create deterministic hash
    content = '_'.join(str(arg) for arg in args)
    hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
    
    return f"site_query_{hash_suffix}_v1"


def batch_get_related(primary_instances, related_model, fk_field, site_filter, filter_type):
    """
    🚀 BATCH GET related objects trong 1 query thay vì N queries
    
    Args:
        primary_instances: List of primary model instances (e.g., SCR_CASE instances)
        related_model: Related model class (e.g., ENR_CASE)
        fk_field: Foreign key field name (e.g., 'USUBJID')
        site_filter, filter_type: Site filtering params
        
    Returns:
        dict: {primary_instance.pk: related_instance or None}
        
    Example:
        screening_cases = [case1, case2, case3]
        enrollment_map = batch_get_related(
            screening_cases, ENR_CASE, 'USUBJID', site_filter, filter_type
        )
        # enrollment_map = {case1.pk: enr1, case2.pk: enr2, case3.pk: None}
    """
    if not primary_instances:
        return {}
    
    # Build filter for related objects
    filter_kwargs = {f"{fk_field}__in": primary_instances}
    
    # Get related objects
    related_qs = get_filtered_queryset(related_model, site_filter, filter_type).filter(**filter_kwargs)
    
    # Build map: primary_instance -> related_instance
    related_map = {}
    for related_obj in related_qs:
        fk_value = getattr(related_obj, fk_field)
        if hasattr(fk_value, 'pk'):
            # ForeignKey case
            related_map[fk_value.pk] = related_obj
        else:
            # Direct value case
            related_map[fk_value] = related_obj
    
    # Fill in None for instances without related objects
    result = {}
    for instance in primary_instances:
        result[instance.pk] = related_map.get(instance.pk)
    
    logger.info(f"🚀 Batch got {len(related_map)}/{len(primary_instances)} {related_model.__name__} in 1 query")
    
    return result


def batch_check_exists(instances, check_models, fk_field, site_filter, filter_type):
    """
    🚀 BATCH CHECK existence của multiple models
    
    Args:
        instances: List of instances to check against
        check_models: List of model classes to check (e.g., [CLI_CASE, DISCH_CASE, ...])
        fk_field: Foreign key field name
        site_filter, filter_type: Site filtering params
        
    Returns:
        dict: {
            instance.pk: {
                'CLI_CASE': bool,
                'DISCH_CASE': bool,
                ...
            }
        }
    """
    if not instances:
        return {}
    
    results = {instance.pk: {} for instance in instances}
    
    # Query each model once
    for model in check_models:
        filter_kwargs = {f"{fk_field}__in": instances}
        existing_pks = set(
            get_filtered_queryset(model, site_filter, filter_type)
            .filter(**filter_kwargs)
            .values_list(fk_field, flat=True)
        )
        
        # Update results
        for instance in instances:
            instance_pk = instance.pk
            results[instance_pk][model.__name__] = instance_pk in existing_pks
    
    logger.info(f"🚀 Batch checked {len(check_models)} models for {len(instances)} instances")
    
    return results


def invalidate_cache(model_name=None, site_filter=None):
    """
    🗑️ Invalidate cache khi có data changes
    
    Args:
        model_name: Specific model to invalidate (None = all)
        site_filter: Specific site filter (None = all)
    """
    if model_name and site_filter:
        # Invalidate specific cache
        pattern = f"site_query_*{model_name}*{site_filter}*"
        cache.delete_pattern(pattern)
        logger.info(f"🗑️ Invalidated cache: {model_name} @ {site_filter}")
    else:
        # Invalidate all site query cache
        cache.delete_pattern("site_query_*")
        logger.info(f"🗑️ Invalidated all site query cache")


def get_site_filtered_object_or_404(model, site_filter, filter_type, **kwargs):
    """
    🚀 OPTIMIZED: Get single object with site filtering - DIRECT query, no bulk cache
    
    This function queries DIRECTLY for the specific object instead of loading
    all objects into cache then filtering. Much faster for single object lookups.
    
    Compatible with old function signature: get_site_filtered_object_or_404(model, site_id, USUBJID=...)
    
    Args:
        model: Django model class
        site_filter: 'all' | str | list (site IDs)
        filter_type: 'all' | 'single' | 'multiple'
        **kwargs: Lookup parameters (e.g., USUBJID='xxx')
    
    Returns:
        Single model instance
        
    Raises:
        PermissionDenied: If object not found or access denied
    """
    # Handle old signature: get_site_filtered_object_or_404(SCR_CASE, site_id, USUBJID=usubjid)
    if isinstance(site_filter, str) and filter_type not in ['all', 'single', 'multiple']:
        # Old signature: (model, site_id, **kwargs)
        old_site_id = site_filter
        old_kwargs = {filter_type: kwargs.popitem()[1]} if kwargs else {}
        
        # Determine filter type from site_id
        if old_site_id == 'all':
            actual_filter_type = 'all'
            actual_site_filter = 'all'
        else:
            actual_filter_type = 'single'
            actual_site_filter = old_site_id
        
        site_filter = actual_site_filter
        filter_type = actual_filter_type
        kwargs = old_kwargs
    
    # 🚀 DIRECT QUERY - Skip cache, query exactly what we need
    try:
        # Apply site filter using site manager (supports models with/without SITEID field)
        if filter_type == 'all':
            # No site filter needed
            base_qs = model.objects.using(DB_ALIAS)
        else:
            # Use site manager which handles both SITEID and USUBJID-based filtering
            if filter_type == 'single':
                base_qs = model.site_objects.using(DB_ALIAS).filter_by_site(site_filter)
            else:  # filter_type == 'multiple'
                if not site_filter:
                    # Empty site filter - return nothing
                    base_qs = model.objects.using(DB_ALIAS).none()
                else:
                    base_qs = model.site_objects.using(DB_ALIAS).filter_by_site(site_filter)
        
        obj = base_qs.get(**kwargs)
        logger.debug(f"[{model.__name__}] Direct query: found {kwargs}")
        return obj
        
    except model.DoesNotExist:
        logger.warning(
            f"[{model.__name__}] Object not found. "
            f"Filter: {site_filter}, Lookup: {kwargs}"
        )
        raise PermissionDenied(
            f"Object not found or access denied (Site: {site_filter})"
        )