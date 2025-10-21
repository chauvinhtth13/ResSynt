# # backend/api/base/helpers.py
# """
# Helper functions for views
# """
# import logging
# from typing import Dict, Any, List
# from django.utils import translation
# from django.utils.translation import gettext_lazy as _

# from backends.tenancy.models import StudySite, StudyMembership
# from backends.tenancy.utils.tenancy_utils import TenancyUtils
# from .constants import AppConstants, SessionKeys

# logger = logging.getLogger(__name__)


# def build_dashboard_context(
#     request, 
#     study, 
#     user_membership, 
#     user_permissions, 
#     user_site_codes
# ) -> Dict[str, Any]:
#     """
#     Build context dictionary for dashboard view.
    
#     Args:
#         request: HTTP request object
#         study: Study object
#         user_membership: StudyMembership object
#         user_permissions: Set of permission strings
#         user_site_codes: List of site codes user has access to
        
#     Returns:
#         Dictionary with all context data for dashboard
#     """
#     current_lang = translation.get_language() or AppConstants.DEFAULT_LANGUAGE
    
#     # Parse group name to extract role
#     group_name = user_membership.group.name if user_membership.group else "No Role"
#     # Extract role name from format "43EN_Admin" -> "Admin"
#     role_display = group_name.split('_', 1)[1] if '_' in group_name else group_name
    
#     return {
#         # Study information
#         'study': study,
#         'study_code': study.code,
#         'study_name': study.safe_translation_getter('name', language_code=current_lang),
        
#         # User information
#         'user': request.user,
#         'user_full_name': request.user.get_full_name() or request.user.username,
#         'user_role': role_display,  
#         'user_role_code': group_name,  
        
#         # Access control
#         'can_access_all_sites': user_membership.can_access_all_sites,
#         'user_sites': user_site_codes,
#         'user_site_count': _('All Sites') if user_membership.can_access_all_sites else len(user_site_codes),
        
#         # Permissions
#         'permissions': user_permissions,
#         'can_view_data': 'data.view' in user_permissions,
#         'can_create_data': 'data.create' in user_permissions,
#         'can_update_data': 'data.update' in user_permissions,
#         'can_delete_data': 'data.delete' in user_permissions,
#         'can_view_reports': 'reports.view' in user_permissions,
#         'can_view_analytics': 'analytics.view' in user_permissions,
#         'can_view_audit': 'audit.view' in user_permissions,
#         'can_manage_study': 'study.manage' in user_permissions,
#         'can_manage_users': 'study.users' in user_permissions,
        
#         # Additional info
#         'last_login': request.user.last_login,
#     }


# def add_sites_to_context(
#     context: Dict[str, Any],
#     study,
#     user_membership,
#     current_lang: str,
#     request
# ) -> None:
#     """
#     Add site information to context dictionary (modifies in-place).
    
#     Args:
#         context: Context dictionary to modify
#         study: Study object
#         user_membership: StudyMembership object
#         current_lang: Current language code
#         request: HTTP request object
#     """
#     # Get all study sites
#     all_study_sites = StudySite.objects.filter(
#         study=study
#     ).select_related('site').order_by('site__code')
    
#     # Determine accessible sites
#     if user_membership.can_access_all_sites:
#         accessible_sites = all_study_sites
#     else:
#         accessible_sites = user_membership.study_sites.select_related('site').order_by('site__code')
    
#     # Format all sites
#     context['all_sites'] = [
#         {
#             'id': ss.site.id,
#             'code': ss.site.code,
#             'name': ss.site.safe_translation_getter('name', language_code=current_lang),
#         }
#         for ss in all_study_sites
#     ]
    
#     # Format accessible sites
#     context['accessible_sites'] = [
#         {
#             'id': ss.site.id,
#             'code': ss.site.code,
#             'name': ss.site.safe_translation_getter('name', language_code=current_lang),
#         }
#         for ss in accessible_sites
#     ]
    
#     # Resolve current active site
#     current_site_code = getattr(request, 'current_site', None)
#     if not current_site_code and hasattr(request, 'session'):
#         current_site_code = request.session.get(SessionKeys.CURRENT_SITE)
#     if not current_site_code:
#         current_site_code = request.GET.get('site') or request.POST.get('site')
    
#     current_site_obj = None
#     if current_site_code:
#         # Look in accessible sites first
#         for s in context['accessible_sites']:
#             if s['code'] == current_site_code:
#                 current_site_obj = s
#                 break
        
#         # Fall back to all sites
#         if not current_site_obj:
#             for s in context['all_sites']:
#                 if s['code'] == current_site_code:
#                     current_site_obj = s
#                     break

#     context['current_site'] = current_site_obj
    
#     # Set default site if none selected
#     if not current_site_obj:
#         try:
#             membership_first = user_membership.study_sites.select_related('site').first()
#             if membership_first:
#                 context['current_site'] = {
#                     'id': membership_first.site.id,
#                     'code': membership_first.site.code,
#                     'name': membership_first.site.safe_translation_getter('name', language_code=current_lang)
#                 }
#         except Exception as e:
#             logger.warning(f"Could not set default site: {e}")


# def get_user_studies_list(user, current_lang: str) -> List[Dict[str, Any]]:
#     """
#     Get formatted list of user studies.
    
#     Args:
#         user: User object
#         current_lang: Current language code
        
#     Returns:
#         List of dictionaries with study info
#     """
#     try:
#         user_studies = TenancyUtils.get_user_studies(user)
        
#         # Set language for each study
#         for s in user_studies:
#             try:
#                 s.set_current_language(AppConstants.DEFAULT_LANGUAGE)
#             except Exception:
#                 pass
        
#         # Format studies
#         return [
#             {
#                 'id': s.pk,
#                 'code': s.code,
#                 'name': s.safe_translation_getter('name', language_code=current_lang)
#             }
#             for s in user_studies
#         ]
#     except Exception as e:
#         logger.error(f"Error getting user studies: {e}")
#         return []


# def get_study_folder_path(study_code: str) -> str:
#     """
#     Get the folder path for study-specific files.
    
#     Args:
#         study_code: Study code
        
#     Returns:
#         Folder path string
#     """
#     return f'studies/study_{study_code.lower()}'