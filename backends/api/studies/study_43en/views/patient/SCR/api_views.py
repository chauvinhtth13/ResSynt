# backends/api/studies/study_43en/views/patient/SCR/api_views.py
"""
API endpoints for screening operations
"""
import logging
import re
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from backends.studies.study_43en.models.patient import SCR_CASE
from backends.studies.study_43en.utils.permission_decorators import check_site_permission

logger = logging.getLogger(__name__)


@login_required
@require_POST
def generate_scrid(request):
    """
    API endpoint to generate next SCRID for a given site
    
    Returns JSON:
    {
        "success": true,
        "scrid": "PS-003-0001",
        "siteid": "003"
    }
    """
    siteid = request.POST.get('siteid', '').strip()
    
    # Validate siteid
    if not siteid or siteid not in ['003', '020', '011']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid SITEID'
        }, status=400)
    
    # SECURITY FIX: Check user's ACTUAL site permissions
    if not check_site_permission(request, siteid):
        user_sites = getattr(request, 'user_sites', set())
        logger.warning(
            f"🚨 API SECURITY: User {request.user.username} "
            f"(accessible_sites={user_sites}) "
            f"attempted to generate SCRID for unauthorized site {siteid}"
        )
        return JsonResponse({
            'success': False,
            'error': f'No permission for site {siteid}'
        }, status=403)
    
    try:
        # Get all existing SCRIDs for this site
        site_cases = SCR_CASE.objects.filter(
            SCRID__startswith=f'PS-{siteid}-'
        ).values_list('SCRID', flat=True)
        
        max_num = 0
        for scrid in site_cases:
            # Extract number from PS-SITEID-XXXX
            m = re.match(rf'PS-{siteid}-(\d+)', str(scrid))
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
        
        # Generate new SCRID with format PS-SITEID-0001
        new_scrid = f"PS-{siteid}-{max_num + 1:04d}"
        
        logger.info(f"Generated SCRID: {new_scrid} for site {siteid}")
        
        return JsonResponse({
            'success': True,
            'scrid': new_scrid,
            'siteid': siteid
        })
        
    except Exception as e:
        logger.error(f"Error generating SCRID: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
