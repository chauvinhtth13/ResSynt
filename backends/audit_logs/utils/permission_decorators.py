# backends/audit_logs/utils/permission_decorators.py
"""
Permission decorators for CRF views
 FIXED: Use TenancyUtils for permission checking
"""
import logging
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from backends.tenancy.utils import TenancyUtils  #  IMPORT

logger = logging.getLogger(__name__)


def require_study_permission(permission_codename: str, redirect_to: str = None):
    """
    Check permission using TenancyUtils
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            study = getattr(request, 'study', None)
            
            if not study:
                logger.warning(f"No study context for {request.user.username}")
                messages.error(request, 'No study context found')
                return redirect('select_study')
            
            #  Use TenancyUtils
            has_permission = TenancyUtils.user_has_permission(
                request.user, 
                study, 
                permission_codename
            )
            
            if not has_permission:
                logger.warning(
                    f"Permission denied: {request.user.username} -> "
                    f"study_{study.code.lower()}.{permission_codename}"
                )
                
                messages.error(
                    request,
                    f'Bạn không có quyền truy cập! (Required: {permission_codename})'
                )
                
                if redirect_to:
                    return redirect(redirect_to)
                else:
                    return redirect('study_43en:home_dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_crf_permission(action: str, model_name: str, redirect_to: str = None):
    """Build permission and check using TenancyUtils"""
    # Django stores permissions with lowercase model names
    permission_codename = f'{action}_{model_name.lower()}'
    return require_study_permission(permission_codename, redirect_to)


def require_crf_view(model_name: str, redirect_to: str = None):
    """Shortcut for view permission"""
    return require_crf_permission('view', model_name, redirect_to)


def require_crf_add(model_name: str, redirect_to: str = None):
    """Shortcut for add permission"""
    return require_crf_permission('add', model_name, redirect_to)


def require_crf_change(model_name: str, redirect_to: str = None):
    """Shortcut for change permission"""
    return require_crf_permission('change', model_name, redirect_to)


def require_crf_delete(model_name: str, redirect_to: str = None):
    """Shortcut for delete permission"""
    return require_crf_permission('delete', model_name, redirect_to)

def get_action_display(action: str) -> str:
    """Get Vietnamese display name for action"""
    action_map = {
        'view': 'xem',
        'add': 'thêm',
        'change': 'chỉnh sửa',
        'delete': 'xóa',
    }
    return action_map.get(action, action)


def get_model_display(model_name: str) -> str:
    """Get display name for model"""
    model_map = {
        'scr_case': 'Screening Case',
        'enr_case': 'Enrollment Case',
        'cli_case': 'Clinical Case',
        'disch_case': 'Discharge',
        'endcasecrf': 'End Case CRF',
    }
    return model_map.get(model_name, model_name)


def permission_context_processor(request):
    """Template context processor"""
    def has_perm(action: str, model_name: str) -> bool:
        study = getattr(request, 'study', None)
        if not study:
            return False
        
        permission_codename = f'{action}_{model_name}'
        return TenancyUtils.user_has_permission(request.user, study, permission_codename)
    
    return {
        'has_perm': has_perm,
    }


# Keep site access functions...
def check_site_access(get_site_from: str = 'instance'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_site = request.session.get('selected_site_id', 'all')
            
            if user_site == 'all':
                return view_func(request, *args, **kwargs)
            
            if get_site_from == 'param':
                site_id = kwargs.get('site_id') or request.GET.get('site_id')
                if site_id and site_id != user_site:
                    logger.warning(
                        f"Site access denied: {request.user.username} "
                        f"(site={user_site}) -> target={site_id}"
                    )
                    messages.error(request, 'Bạn không có quyền truy cập site này!')
                    return redirect('study_43en:home_dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def check_site_permission(request, siteid: str) -> bool:
    """
    SECURITY: Check if user has permission to access/create for a specific site
    
    This is a HELPER function that returns True/False without side effects.
    Use for validation in views and APIs.
    
    Args:
        request: HttpRequest with site context (from middleware)
        siteid: Site ID to check (e.g., '003', '011', '020')
        
    Returns:
        True if allowed, False if denied
    """
    # Get user's ACTUAL accessible sites from middleware context
    user_sites = getattr(request, 'user_sites', set())
    can_access_all = getattr(request, 'can_access_all_sites', False)
    
    # Super admin OR site in user's accessible list
    if can_access_all or siteid in user_sites:
        return True
    
    return False


def check_instance_site_access(request, instance, redirect_to: str = None):
    """
    SECURITY FIX: Check if user ACTUALLY has permission to access this site
    
    ❌ OLD LOGIC: Only checked session['selected_site_id'] → BYPASS-able!
     NEW LOGIC: Check against user's actual site permissions from middleware
    
    Args:
        request: HttpRequest with site context (from middleware)
        instance: Model instance with SITEID field
        redirect_to: Optional redirect target on denial
        
    Returns:
        True if allowed, redirect/exception otherwise
    """
    instance_site = getattr(instance, 'SITEID', None)
    
    if not instance_site:
        logger.warning(f"Instance has no SITEID: {instance}")
        return True  # Safe fallback if no site field
    
    # Use helper function for actual check
    if check_site_permission(request, instance_site):
        logger.debug(
            f"Site access granted: {request.user.username} -> {instance_site}"
        )
        return True
    
    # ❌ ACCESS DENIED
    user_sites = getattr(request, 'user_sites', set())
    can_access_all = getattr(request, 'can_access_all_sites', False)
    
    logger.warning(
        f"🚨 SECURITY: Site access DENIED! "
        f"User={request.user.username} "
        f"(accessible_sites={user_sites}, can_access_all={can_access_all}) "
        f"attempted to access SITEID={instance_site}"
    )
    
    # Format site list nicely
    allowed_sites = ", ".join(sorted(user_sites)) if user_sites else "không có site nào"
    
    messages.error(
        request, 
        f'Bạn không có quyền truy cập site {instance_site}. '
        f'Các site bạn được truy cập: {allowed_sites}.'
    )
    
    if redirect_to:
        return redirect(redirect_to)
    else:
        raise PermissionDenied(
            f"User {request.user.username} with sites {user_sites} "
            f"cannot access instance from site {instance_site}"
        )
