# backends/api/studies/study_43en/views/contact/SCR/api_views.py
"""
API endpoints for contact screening operations
"""
import logging
import re
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from backends.studies.study_43en.models.contact import SCR_CONTACT
from backends.audit_log.utils.permission_decorators import check_site_permission

logger = logging.getLogger(__name__)


@login_required
@require_POST
def generate_contact_scrid(request):
    """
    API endpoint to generate next Contact SCRID for a given site
    
    Returns JSON:
    {
        "success": true,
        "scrid": "CS-003-0001",
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
    
    # 🔒 SECURITY FIX: Check user's ACTUAL site permissions
    if not check_site_permission(request, siteid):
        user_sites = getattr(request, 'user_sites', set())
        logger.warning(
            f"🚨 API SECURITY: User {request.user.username} "
            f"(accessible_sites={user_sites}) "
            f"attempted to generate contact SCRID for unauthorized site {siteid}"
        )
        return JsonResponse({
            'success': False,
            'error': f'No permission for site {siteid}'
        }, status=403)
    
    try:
        # Get all existing SCRIDs for this site
        site_contacts = SCR_CONTACT.objects.filter(
            SCRID__startswith=f'CS-{siteid}-'
        ).values_list('SCRID', flat=True)
        
        max_num = 0
        for scrid in site_contacts:
            # Extract number from CS-SITEID-XXXX
            m = re.match(rf'CS-{siteid}-(\d+)', str(scrid))
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
        
        # Generate new SCRID with format CS-SITEID-0001
        new_scrid = f"CS-{siteid}-{max_num + 1:04d}"
        
        logger.info(f" Generated Contact SCRID: {new_scrid} for site {siteid}")
        
        return JsonResponse({
            'success': True,
            'scrid': new_scrid,
            'siteid': siteid
        })
        
    except Exception as e:
        logger.error(f"❌ Error generating Contact SCRID: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
