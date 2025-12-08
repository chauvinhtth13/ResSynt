# File: backends/studies/study_43en/utils/site_utils.py

"""
Site Filtering Utilities for Views
===================================

High-level helper functions matching dashboard.py logic
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)

DB_ALIAS = 'db_study_43en'


def get_site_filter_params(request):
    """
     REFACTORED: Single source of truth - uses middleware context
    
    Determine site filter strategy from UnifiedTenancyMiddleware context.
    Middleware ALWAYS injects site context for Study 43EN (after merge).
    
    Returns:
        tuple: (site_filter, filter_type)
            - site_filter: 'all' | str | list
            - filter_type: 'all' | 'single' | 'multiple'
    
    Examples:
        site_filter, filter_type = get_site_filter_params(request)
        
        # filter_type='all' → site_filter='all' (super admin sees ALL sites)
        # filter_type='single' → site_filter='003' (user selected specific site)
        # filter_type='multiple' → site_filter=['003', '011'] (multi-site user)
    """
    #  Get from UnifiedTenancyMiddleware context (always present)
    selected_site_id = getattr(request, 'selected_site_id', 'all')
    can_access_all = getattr(request, 'can_access_all_sites', False)
    user_site_codes = list(getattr(request, 'user_sites', set()))
    
    # Strategy 1: Single site selected
    if selected_site_id and selected_site_id != 'all':
        logger.debug(f"Site filter: single '{selected_site_id}'")
        return (selected_site_id, 'single')
    
    # Strategy 2: Super admin with 'all' → see ALL sites in study
    elif can_access_all and selected_site_id == 'all':
        logger.debug(f"Site filter: all (super admin)")
        return ('all', 'all')
    
    # Strategy 3: Multi-site user with 'all' → see only THEIR sites
    elif selected_site_id == 'all' and user_site_codes:
        logger.debug(f"Site filter: multiple {user_site_codes}")
        return (user_site_codes, 'multiple')
    
    # Strategy 4: Fallback (no sites)
    else:
        logger.debug(f"Site filter: multiple {user_site_codes} (fallback)")
        return (user_site_codes, 'multiple')


def get_filtered_queryset(model, site_filter, filter_type):
    """
     COPY FROM DASHBOARD
    Get filtered queryset matching dashboard logic
    
    Args:
        model: Django model class
        site_filter: 'all' | str | list
        filter_type: 'all' | 'single' | 'multiple'
    
    Returns:
        Filtered QuerySet using db_study_43en
    """
    if filter_type == 'all':
        logger.debug(f"[{model.__name__}] Query all sites")
        return model.objects.using(DB_ALIAS)
    
    elif filter_type == 'multiple':
        logger.debug(f"[{model.__name__}] Query multiple sites: {site_filter}")
        
        if not site_filter:
            logger.warning(f"[{model.__name__}] Empty site filter - returning empty")
            return model.objects.using(DB_ALIAS).none()
        
        # Use manager's filter_by_site which handles multiple sites
        return model.site_objects.using(DB_ALIAS).filter_by_site(site_filter)
    
    else:  # filter_type == 'single'
        logger.debug(f"[{model.__name__}] Query single site: {site_filter}")
        return model.site_objects.using(DB_ALIAS).filter_by_site(site_filter)


def get_site_filtered_object_or_404(model, site_filter, filter_type, **kwargs):
    """
    Get object with site filtering and 404 handling
    
    Compatible with old function signature: get_site_filtered_object_or_404(model, site_id, USUBJID=...)
    """
    # Handle old signature: get_site_filtered_object_or_404(SCR_CASE, site_id, USUBJID=usubjid)
    if isinstance(site_filter, str) and filter_type not in ['all', 'single', 'multiple']:
        # Old signature: (model, site_id, **kwargs)
        # site_filter is actually site_id
        # filter_type is actually first kwarg key
        old_site_id = site_filter
        old_kwargs = {filter_type: kwargs.popitem()[1]} if kwargs else {}
        
        # Determine filter type from site_id
        if old_site_id == 'all':
            actual_filter_type = 'all'
        else:
            actual_filter_type = 'single'
        
        queryset = get_filtered_queryset(model, old_site_id, actual_filter_type)
        kwargs = old_kwargs
    else:
        # New signature
        queryset = get_filtered_queryset(model, site_filter, filter_type)
    
    try:
        obj = queryset.get(**kwargs)
        return obj
    except model.DoesNotExist:
        logger.warning(
            f"[{model.__name__}] Object not found. "
            f"Filter: {site_filter}, Lookup: {kwargs}"
        )
        raise PermissionDenied(
            f"Object not found or access denied (Site: {site_filter})"
        )