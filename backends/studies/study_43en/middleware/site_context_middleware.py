# # backends/studies/study_43en/middleware/site_context_middleware.py
# """
# Site Context Middleware for Study 43EN - REFACTORED VERSION

# 🎯 PURPOSE:
# Auto-inject site filtering context into request object using TenancyUtils.

#  REFACTORED:
# - Uses TenancyUtils.get_user_sites() instead of custom caching
# - Uses User.get_study_membership() instead of custom query
# - Removed duplicate code
# - Lighter and more maintainable

#  WHAT IT DOES:
# 1. Injects site context into request:
#    - request.user_sites (set of site codes)
#    - request.selected_site_id ('all' | 'XXX')
#    - request.can_access_all_sites (boolean)
#    - request.user_membership (cached object)
#    - request.study_sites (list, for backwards compatibility)

# 2. All caching handled by TenancyUtils (triple-layer caching)
# 3. Auto-validates selected site from session

#  BENEFITS:
# -  NO code duplication with tenancy
# -  Uses TenancyUtils triple-layer caching
# -  Views just use: request.selected_site_id and request.user_sites
# -  Backwards compatible with existing code

# 📝 USAGE:
# Add to settings.py AFTER UnifiedTenancyMiddleware:

# MIDDLEWARE = [
#     ...
#     'backends.tenancy.middleware.UnifiedTenancyMiddleware',
#     'backends.studies.study_43en.middleware.SiteContextMiddleware',
#     ...
# ]
# """

# import logging
# from typing import Set
# from django.http import HttpRequest, HttpResponse

# #  REFACTORED: Import TenancyUtils instead of rewriting logic
# from backends.tenancy.utils import TenancyUtils

# logger = logging.getLogger(__name__)


# class SiteContextMiddleware:
#     """
#     Lightweight middleware to inject site context into request
    
#      REFACTORED: Uses TenancyUtils for all data access
    
#     Requirements:
#     - Must be placed AFTER UnifiedTenancyMiddleware
#     - User must be authenticated
#     - Study context must exist (request.study)
    
#     Performance:
#     - Uses TenancyUtils triple-layer caching
#     - ~0.3ms overhead per request (cached)
#     - No duplicate caching logic
#     """
    
#     def __init__(self, get_response):
#         self.get_response = get_response
#         logger.debug("SiteContextMiddleware initialized (REFACTORED)")
    
#     def __call__(self, request: HttpRequest) -> HttpResponse:
#         """
#         Main middleware processing
        
#         Order:
#         1. Check prerequisites (auth, study context)
#         2. Load user membership (cached)
#         3. Determine site permissions
#         4. Inject context into request
#         5. Continue to view
#         """
#         # Skip if not authenticated
#         if not request.user or not request.user.is_authenticated:
#             return self.get_response(request)
        
#         # Skip if no study context (public paths, admin, etc.)
#         if not hasattr(request, 'study') or not request.study:
#             return self.get_response(request)
        
#         # Skip if study is not 43EN (this middleware is study-specific)
#         if request.study.code != '43EN':
#             return self.get_response(request)
        
#         # Inject site context
#         self._inject_site_context(request)
        
#         return self.get_response(request)
    
#     # ==========================================
#     # SITE CONTEXT INJECTION
#     # ==========================================
    
#     def _inject_site_context(self, request: HttpRequest):
#         """
#          REFACTORED: Inject site filtering context using TenancyUtils
        
#         Sets the following attributes:
#         - request.user_membership: StudyMembership object (from User model)
#         - request.can_access_all_sites: Boolean
#         - request.user_sites: Set of accessible site codes {'003', '011', '020'}
#         - request.selected_site_id: Current site selection ('all' | 'XXX')
#         - request.study_sites: List (for backwards compatibility)
#         """
#         study = request.study
#         user = request.user
        
#         try:
#             #  USE: User.get_study_membership() instead of custom query
#             membership = user.get_study_membership(study)
            
#             if not membership:
#                 # No membership - set safe defaults
#                 self._set_default_context(request)
#                 return
            
#             # Inject membership object
#             request.user_membership = membership
            
#             # Determine if user can access all sites
#             can_access_all = membership.can_access_all_sites
#             request.can_access_all_sites = can_access_all
            
#             #  USE: TenancyUtils.get_user_sites() instead of custom logic
#             user_sites_list = TenancyUtils.get_user_sites(user, study)
#             user_sites = set(user_sites_list)
            
#             request.user_sites = user_sites
#             request.study_sites = user_sites_list  # List format (backwards compat)
            
#             # Get or initialize selected site
#             selected_site = self._get_selected_site(request, can_access_all, user_sites)
#             request.selected_site_id = selected_site
            
#             logger.debug(
#                 f"Site context injected: User={user.pk} | "
#                 f"Sites={user_sites} | Selected={selected_site} | "
#                 f"CanAccessAll={can_access_all}"
#             )
            
#         except Exception as e:
#             logger.error(f"Error injecting site context: {e}", exc_info=True)
#             self._set_default_context(request)
    
#     # ==========================================
#     #  REMOVED: _get_user_membership() 
#     # → Now using User.get_study_membership()
#     # ==========================================
    
#     # ==========================================
#     #  REMOVED: _get_all_study_sites()
#     # → Now using TenancyUtils.get_user_sites()
#     # ==========================================
    
#     def _get_selected_site(
#         self, 
#         request: HttpRequest, 
#         can_access_all: bool, 
#         user_sites: Set[str]
#     ) -> str:
#         """
#         Get or initialize selected site from session
        
#          KEPT: This logic is specific to site selection UI behavior
        
#         Auto-selection logic:
#         - If can_access_all: default to 'all'
#         - If single site: auto-select that site
#         - If multiple sites: default to 'all' (user sees all their sites)
        
#         Args:
#             request: HttpRequest
#             can_access_all: Boolean
#             user_sites: Set of accessible site codes
            
#         Returns:
#             Selected site code or 'all'
#         """
#         selected_site = request.session.get('selected_site_id')
        
#         if not selected_site:
#             # First time: auto-select based on permissions
#             if can_access_all:
#                 selected_site = 'all'
#             elif len(user_sites) == 1:
#                 # Only one site: auto-select it
#                 selected_site = list(user_sites)[0]
#             elif len(user_sites) > 1:
#                 # Multiple sites → default to 'all' (user sees all their sites)
#                 selected_site = 'all'
#             else:
#                 # No sites (shouldn't happen, but safe default)
#                 selected_site = 'all'
            
#             request.session['selected_site_id'] = selected_site
#             logger.info(f"Auto-selected site: {selected_site} for user {request.user.pk}")
        
#         # Validate selected site
#         if selected_site != 'all' and selected_site not in user_sites and not can_access_all:
#             # Invalid selection: reset to 'all' (show all user's sites)
#             logger.warning(
#                 f"User {request.user.pk} has invalid site selection '{selected_site}', "
#                 f"resetting to 'all' (user sites: {user_sites})"
#             )
#             selected_site = 'all'
#             request.session['selected_site_id'] = selected_site
        
#         return selected_site
    
#     def _set_default_context(self, request: HttpRequest):
#         """
#         Set safe default context when membership not found
        
#         Args:
#             request: HttpRequest
#         """
#         request.user_membership = None
#         request.can_access_all_sites = False
#         request.user_sites = set()
#         request.study_sites = []
#         request.selected_site_id = 'all'
        
#         logger.warning(f"Set default site context for user {request.user.pk}")


# # ==========================================
# # HELPER: Clear Site Cache
# # ==========================================

# def clear_site_cache(user_id: int = None, study_id: int = None):
#     """
#      REFACTORED: Wrapper to TenancyUtils cache clearing
    
#     Clear site context cache using TenancyUtils
    
#     Use this when:
#     - User's site assignments change
#     - User's permissions change
#     - Sites are added/removed from study
    
#     Args:
#         user_id: Optional user ID (clear specific user)
#         study_id: Optional study ID (clear specific study)
    
#     Examples:
#         # Clear specific user's cache
#         clear_site_cache(user_id=123)
        
#         # Clear all caches for study
#         clear_site_cache(study_id=1)
#     """
#     if user_id:
#         #  USE: TenancyUtils.clear_user_cache() instead of custom logic
#         from backends.tenancy.models import User
#         try:
#             user = User.objects.get(pk=user_id)
#             cleared = TenancyUtils.clear_user_cache(user)
#             logger.debug(f"Cleared {cleared} cache keys for user {user_id}")
#         except User.DoesNotExist:
#             logger.warning(f"User {user_id} not found for cache clearing")
    
#     elif study_id:
#         #  USE: TenancyUtils.clear_study_cache() instead of custom logic
#         from backends.tenancy.models import Study
#         try:
#             study = Study.objects.get(pk=study_id)
#             cleared = TenancyUtils.clear_study_cache(study)
#             logger.debug(f"Cleared {cleared} cache keys for study {study_id}")
#         except Study.DoesNotExist:
#             logger.warning(f"Study {study_id} not found for cache clearing")
    
#     else:
#         #  USE: TenancyUtils.clear_all_cache()
#         cleared = TenancyUtils.clear_all_cache()
#         logger.debug(f"Cleared {cleared} cache keys (all)")
