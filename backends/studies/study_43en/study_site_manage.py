# File: backends/studies/study_43en/study_site_manage.py

"""
Site Filtering System for Study 43EN
====================================

QUAN TRỌNG: System này hỗ trợ 3 loại filtering:
1. 'all' - Super admin xem tất cả sites
2. Single site - User thuộc 1 site (string: '003', '011', '020')
3. Multiple sites - User thuộc nhiều sites (list: ['003', '011'])

Usage:
    # Direct usage
    queryset = SCR_CASE.site_objects.filter_by_site('003')  # single
    queryset = SCR_CASE.site_objects.filter_by_site(['003', '011'])  # multiple
    queryset = SCR_CASE.site_objects.filter_by_site('all')  # all
    
    # With database routing
    queryset = SCR_CASE.site_objects.using('db_study_43en').filter_by_site('003')
"""

from django.db import models
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

# Database alias constant
DB_ALIAS = 'db_study_43en'


class SiteFilteredQuerySet(models.QuerySet):
    """
    Custom QuerySet with intelligent site filtering
    
    Automatically detects model structure and applies appropriate filters:
    - Model có SITEID field → filter trực tiếp
    - Model có USUBJID CharField → filter theo prefix (e.g., "003-001")  
    - Model có USUBJID ForeignKey → filter qua related model
    - Model có ENROLLCASE → filter qua enrollment chain
    """
    
    def filter_by_site(self, site_id):
        """
        Filter queryset by SITEID with flexible input support
        
        Args:
            site_id: Can be:
                - None or 'all': Return all (no filter)
                - str: Single site code ('003', '011', '020')
                - list/tuple: Multiple site codes (['003', '011'])
        
        Returns:
            Filtered QuerySet
        
        Examples:
            >>> SCR_CASE.site_objects.filter_by_site('003')
            >>> ENR_CASE.site_objects.filter_by_site(['003', '011'])
            >>> CLI_CASE.site_objects.filter_by_site('all')
        """
        # ==========================================
        # CASE 0: No filter - Return all
        # ==========================================
        if not site_id or site_id == 'all':
            logger.debug(f"[{self.model.__name__}] No site filter (all)")
            return self
        
        model = self.model
        model_name = model.__name__
        
        # ==========================================
        # CASE 1: Multiple Sites (LIST/TUPLE)
        # ==========================================
        if isinstance(site_id, (list, tuple)):
            if len(site_id) == 0:
                logger.warning(f"[{model_name}] Empty site list - returning empty queryset")
                return self.none()
            
            logger.debug(f"[{model_name}] Filtering by multiple sites: {site_id}")
            return self._filter_multiple_sites(site_id)
        
        # ==========================================
        # CASE 2: Single Site (STRING)
        # ==========================================
        logger.debug(f"[{model_name}] Filtering by single site: {site_id}")
        return self._filter_single_site(site_id)
    
    
    def _get_model_fields(self):
        """Get list of model field names"""
        return [f.name for f in self.model._meta.get_fields()]
    
    
    def _filter_multiple_sites(self, site_codes):
        """
        Filter by multiple sites using Q objects (OR conditions)
        
        Strategy Priority:
        1. SITEID field (direct) - Most common for base models
        2. USUBJID CharField - Extract site from prefix
        3. USUBJID ForeignKey - Traverse relationship
        4. ENROLLCASE - Clinical forms reference
        """
        model = self.model
        model_name = model.__name__
        model_fields = self._get_model_fields()
        q_objects = Q()
        
        # ==========================================
        # Strategy 1: Direct SITEID field
        # ==========================================
        if 'SITEID' in model_fields:
            logger.debug(f"[{model_name}] Multiple sites via SITEID field")
            for site_code in site_codes:
                q_objects |= Q(SITEID=site_code)
            return self.filter(q_objects)
        
        # ==========================================
        # Strategy 2: USUBJID CharField
        # ==========================================
        if 'USUBJID' in model_fields:
            field = model._meta.get_field('USUBJID')
            
            if isinstance(field, models.CharField):
                logger.debug(f"[{model_name}] Multiple sites via USUBJID CharField prefix")
                for site_code in site_codes:
                    q_objects |= Q(USUBJID__startswith=f"{site_code}-")
                return self.filter(q_objects)
            
            # ==========================================
            # Strategy 3: USUBJID ForeignKey/OneToOneField
            # ==========================================
            elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
                logger.debug(f"[{model_name}] Multiple sites via USUBJID FK")
                return self._filter_multiple_sites_via_fk(site_codes, field)
        
        # ==========================================
        # Strategy 4: ENROLLCASE (Clinical forms)
        # ==========================================
        if 'ENROLLCASE' in model_fields:
            field = model._meta.get_field('ENROLLCASE')
            if isinstance(field, models.ForeignKey):
                logger.debug(f"[{model_name}] Multiple sites via ENROLLCASE FK chain")
                # ENROLLCASE → ENR_CASE → USUBJID (SCR_CASE) → SITEID
                for site_code in site_codes:
                    q_objects |= Q(ENROLLCASE__USUBJID__SITEID=site_code)
                return self.filter(q_objects)
        
        # ==========================================
        # Strategy 5: LAB_CULTURE_ID (AntibioticSensitivity)
        # ==========================================
        if 'LAB_CULTURE_ID' in model_fields:
            field = model._meta.get_field('LAB_CULTURE_ID')
            if isinstance(field, models.ForeignKey):
                logger.debug(f"[{model_name}] Multiple sites via LAB_CULTURE_ID FK")
                # LAB_CULTURE_ID → LAB_Microbiology → SITEID
                for site_code in site_codes:
                    q_objects |= Q(LAB_CULTURE_ID__SITEID=site_code)
                return self.filter(q_objects)
        
        # ==========================================
        # No valid strategy found
        # ==========================================
        logger.error(f"[{model_name}]  No site filtering strategy found")
        logger.error(f"[{model_name}] Available fields: {model_fields}")
        
        #  CRITICAL: Return empty queryset for security
        return self.none()
    
    
    def _filter_multiple_sites_via_fk(self, site_codes, fk_field):
        """
        Filter multiple sites through ForeignKey relationship
        
        Handles nested FK chains:
        - ENR_CASE → SCR_CASE (USUBJID__SITEID)
        - CLI_CASE → ENR_CASE → SCR_CASE (USUBJID__USUBJID__SITEID)
        """
        model = self.model
        model_name = model.__name__
        related_model = fk_field.related_model
        related_fields = [f.name for f in related_model._meta.get_fields()]
        q_objects = Q()
        
        # Related model has SITEID directly
        if 'SITEID' in related_fields:
            logger.debug(f"[{model_name}] Multiple sites via USUBJID__SITEID")
            for site_code in site_codes:
                q_objects |= Q(USUBJID__SITEID=site_code)
            return self.filter(q_objects)
        
        # Related model has USUBJID (nested FK chain)
        if 'USUBJID' in related_fields:
            related_field = related_model._meta.get_field('USUBJID')
            
            # Related USUBJID is CharField
            if isinstance(related_field, models.CharField):
                logger.debug(f"[{model_name}] Multiple sites via USUBJID__USUBJID prefix")
                for site_code in site_codes:
                    q_objects |= Q(USUBJID__USUBJID__startswith=f"{site_code}-")
                return self.filter(q_objects)
            
            # Double nested FK (rare: CLI_CASE → ENR_CASE → SCR_CASE)
            elif isinstance(related_field, (models.ForeignKey, models.OneToOneField)):
                logger.debug(f"[{model_name}] Multiple sites via double nested FK")
                nested_related_model = related_field.related_model
                nested_fields = [f.name for f in nested_related_model._meta.get_fields()]
                
                if 'SITEID' in nested_fields:
                    for site_code in site_codes:
                        q_objects |= Q(USUBJID__USUBJID__SITEID=site_code)
                else:
                    for site_code in site_codes:
                        q_objects |= Q(USUBJID__USUBJID__USUBJID__startswith=f"{site_code}-")
                
                return self.filter(q_objects)
        
        logger.error(f"[{model_name}]  Cannot resolve FK relationship for multiple sites")
        return self.none()
    
    
    def _filter_single_site(self, site_code):
        """
        Filter by single site
        
        Same strategy priority as multiple sites but with simpler syntax
        """
        model = self.model
        model_name = model.__name__
        model_fields = self._get_model_fields()
        
        # ==========================================
        # Strategy 1: Direct SITEID field
        # ==========================================
        if 'SITEID' in model_fields:
            logger.debug(f"[{model_name}] Single site via SITEID field")
            return self.filter(SITEID=site_code)
        
        # ==========================================
        # Strategy 2: USUBJID CharField
        # ==========================================
        if 'USUBJID' in model_fields:
            field = model._meta.get_field('USUBJID')
            
            if isinstance(field, models.CharField):
                logger.debug(f"[{model_name}] Single site via USUBJID CharField prefix")
                return self.filter(USUBJID__startswith=f"{site_code}-")
            
            # ==========================================
            # Strategy 3: USUBJID ForeignKey/OneToOneField
            # ==========================================
            elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
                logger.debug(f"[{model_name}] Single site via USUBJID FK")
                return self._filter_single_site_via_fk(site_code, field)
        
        # ==========================================
        # Strategy 4: ENROLLCASE (Clinical forms)
        # ==========================================
        if 'ENROLLCASE' in model_fields:
            field = model._meta.get_field('ENROLLCASE')
            if isinstance(field, models.ForeignKey):
                logger.debug(f"[{model_name}] Single site via ENROLLCASE FK chain")
                # ENROLLCASE → ENR_CASE → USUBJID (SCR_CASE) → SITEID
                return self.filter(ENROLLCASE__USUBJID__SITEID=site_code)
        
        # ==========================================
        # Strategy 5: LAB_CULTURE_ID (AntibioticSensitivity)
        # ==========================================
        if 'LAB_CULTURE_ID' in model_fields:
            field = model._meta.get_field('LAB_CULTURE_ID')
            if isinstance(field, models.ForeignKey):
                logger.debug(f"[{model_name}] Single site via LAB_CULTURE_ID FK")
                # LAB_CULTURE_ID → LAB_Microbiology → SITEID
                return self.filter(LAB_CULTURE_ID__SITEID=site_code)
        
        # ==========================================
        # No valid strategy found
        # ==========================================
        logger.error(f"[{model_name}]  No site filtering strategy found")
        logger.error(f"[{model_name}] Available fields: {model_fields}")
        
        #  CRITICAL: Return empty queryset for security
        return self.none()
    
    
    def _filter_single_site_via_fk(self, site_code, fk_field):
        """
        Filter single site through ForeignKey relationship
        
        Handles nested FK chains similar to multiple sites
        """
        model = self.model
        model_name = model.__name__
        related_model = fk_field.related_model
        related_fields = [f.name for f in related_model._meta.get_fields()]
        
        # Related model has SITEID directly
        if 'SITEID' in related_fields:
            logger.debug(f"[{model_name}] Single site via USUBJID__SITEID")
            return self.filter(USUBJID__SITEID=site_code)
        
        # Related model has USUBJID (nested FK chain)
        if 'USUBJID' in related_fields:
            related_field = related_model._meta.get_field('USUBJID')
            
            # Related USUBJID is CharField
            if isinstance(related_field, models.CharField):
                logger.debug(f"[{model_name}] Single site via USUBJID__USUBJID prefix")
                return self.filter(USUBJID__USUBJID__startswith=f"{site_code}-")
            
            # Double nested FK
            elif isinstance(related_field, (models.ForeignKey, models.OneToOneField)):
                logger.debug(f"[{model_name}] Single site via double nested FK")
                nested_related_model = related_field.related_model
                nested_fields = [f.name for f in nested_related_model._meta.get_fields()]
                
                if 'SITEID' in nested_fields:
                    return self.filter(USUBJID__USUBJID__SITEID=site_code)
                else:
                    return self.filter(USUBJID__USUBJID__USUBJID__startswith=f"{site_code}-")
        
        logger.error(f"[{model_name}]  Cannot resolve FK relationship for single site")
        return self.none()


#  FIXED CLASS NAME
class SiteFilteredManager(models.Manager):
    """
    Custom Manager with site filtering capabilities
    
    Automatically attached to all models via AuditFieldsMixin
    
    Provides:
        - get_queryset(): Returns SiteFilteredQuerySet
        - filter_by_site(): Shortcut for site filtering
        - using(): Database routing support
    
    Usage:
        class MyModel(AuditFieldsMixin):
            # site_objects is automatically available
            pass
        
        # In views
        queryset = MyModel.site_objects.filter_by_site('003')
        queryset = MyModel.site_objects.using('db_study_43en').filter_by_site('003')
    """
    
    def get_queryset(self):
        """Return custom queryset with site filtering"""
        return SiteFilteredQuerySet(self.model, using=self._db)
    
    def filter_by_site(self, site_id):
        """
        Filter queryset by SITEID
        
        Args:
            site_id: 'all', single site code, or list of site codes
        
        Returns:
            Filtered QuerySet
        
        Examples:
            >>> Model.site_objects.filter_by_site('003')
            >>> Model.site_objects.filter_by_site(['003', '011'])
            >>> Model.site_objects.filter_by_site('all')
        """
        return self.get_queryset().filter_by_site(site_id)
    
    def using(self, alias):
        """
        Support database routing with method chaining
        
        Usage:
            Model.site_objects.using('db_study_43en').filter_by_site('003')
        """
        return self.get_queryset().using(alias)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def build_site_q_filter(model, site_codes):
    """
    Build Q object for multiple sites - Utility function
    
    Args:
        model: Django model class
        site_codes: List of site codes or single site code
    
    Returns:
        Q object with OR conditions
    
    Usage:
        q_filter = build_site_q_filter(SCR_CASE, ['003', '011'])
        queryset = SCR_CASE.objects.filter(q_filter)
    """
    if isinstance(site_codes, str):
        site_codes = [site_codes]
    
    model_fields = [f.name for f in model._meta.get_fields()]
    q_objects = Q()
    
    # Strategy 1: SITEID
    if 'SITEID' in model_fields:
        for site_code in site_codes:
            q_objects |= Q(SITEID=site_code)
    
    # Strategy 2: USUBJID CharField
    elif 'USUBJID' in model_fields:
        field = model._meta.get_field('USUBJID')
        
        if isinstance(field, models.CharField):
            for site_code in site_codes:
                q_objects |= Q(USUBJID__startswith=f"{site_code}-")
        
        elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
            related_fields = [f.name for f in field.related_model._meta.get_fields()]
            
            if 'SITEID' in related_fields:
                for site_code in site_codes:
                    q_objects |= Q(USUBJID__SITEID=site_code)
            else:
                for site_code in site_codes:
                    q_objects |= Q(USUBJID__USUBJID__startswith=f"{site_code}-")
    
    # Strategy 3: ENROLLCASE
    elif 'ENROLLCASE' in model_fields:
        for site_code in site_codes:
            q_objects |= Q(ENROLLCASE__USUBJID__SITEID=site_code)
    
    # Strategy 4: LAB_CULTURE_ID (for AntibioticSensitivity)
    elif 'LAB_CULTURE_ID' in model_fields:
        for site_code in site_codes:
            q_objects |= Q(LAB_CULTURE_ID__SITEID=site_code)
    
    return q_objects


def get_site_field_info(model):
    """
    Diagnostic function to check how a model can be filtered by site
    
    Args:
        model: Django model class
    
    Returns:
        dict with filtering strategy information
    
    Usage:
        info = get_site_field_info(SCR_CASE)
        print(info['filter_strategy'])
    """
    model_fields = [f.name for f in model._meta.get_fields()]
    
    info = {
        'model_name': model.__name__,
        'has_siteid': 'SITEID' in model_fields,
        'has_usubjid': 'USUBJID' in model_fields,
        'has_enrollcase': 'ENROLLCASE' in model_fields,
        'usubjid_type': None,
        'filter_strategy': None,
        'can_filter_by_site': False
    }
    
    # Check SITEID
    if info['has_siteid']:
        info['filter_strategy'] = 'Direct SITEID field'
        info['can_filter_by_site'] = True
        return info
    
    # Check USUBJID
    if info['has_usubjid']:
        field = model._meta.get_field('USUBJID')
        info['usubjid_type'] = type(field).__name__
        
        if isinstance(field, models.CharField):
            info['filter_strategy'] = 'USUBJID CharField prefix (e.g., "003-001")'
            info['can_filter_by_site'] = True
        elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
            related_fields = [f.name for f in field.related_model._meta.get_fields()]
            if 'SITEID' in related_fields:
                info['filter_strategy'] = 'Via USUBJID__SITEID'
            else:
                info['filter_strategy'] = 'Via USUBJID__USUBJID__startswith'
            info['can_filter_by_site'] = True
        return info
    
    # Check ENROLLCASE
    if info['has_enrollcase']:
        info['filter_strategy'] = 'Via ENROLLCASE__USUBJID__SITEID'
        info['can_filter_by_site'] = True
        return info
    
    # Check LAB_CULTURE_ID (AntibioticSensitivity)
    if 'LAB_CULTURE_ID' in model_fields:
        field = model._meta.get_field('LAB_CULTURE_ID')
        if isinstance(field, models.ForeignKey):
            info['filter_strategy'] = 'Via LAB_CULTURE_ID__SITEID'
            info['can_filter_by_site'] = True
            return info
    
    # No filtering available
    info['filter_strategy'] = 'No site filtering available '
    info['can_filter_by_site'] = False
    
    return info