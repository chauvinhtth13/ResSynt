# backends/api/base/account/lockout.py
"""
Custom lockout handler for django-axes.
Returns login page with inline error instead of redirect.

This module provides a security-focused lockout response that:
1. Keeps user on login page (no redirect)
2. Displays clear lockout message
3. Disables form to prevent further attempts
4. Logs security events
5. Optionally triggers alerts
"""
import logging
from typing import Dict, Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def lockout_response(
    request: HttpRequest,
    credentials: Dict[str, Any],
    *args,
    **kwargs
) -> HttpResponse:
    """
    Custom lockout handler that renders login page with inline error message.
    
    This is called by axes when a user is locked out. Instead of redirecting
    to a separate lockout page, we render the login form with an error message.
    
    Args:
        request: The HttpRequest object
        credentials: Dict containing authentication credentials (username/login)
        *args, **kwargs: Additional arguments from axes
        
    Returns:
        HttpResponse: Login page with lockout error (status 403)
    
    Security features:
        - Returns 403 Forbidden status
        - Logs lockout event with IP
        - Form is disabled in template
        - Clear user messaging
    """
    from .forms import LockoutAwareLoginForm
    
    # Debug: Log what axes is passing
    logger.debug(f"LOCKOUT DEBUG - credentials: {credentials}")
    logger.debug(f"LOCKOUT DEBUG - args: {args}")
    logger.debug(f"LOCKOUT DEBUG - kwargs: {kwargs}")
    if request:
        logger.debug(f"LOCKOUT DEBUG - POST data: {dict(request.POST)}")
    
    # Extract username from credentials or request POST data
    username = _get_username_from_credentials(credentials)
    
    # Fallback: try to get from POST data if credentials is empty
    if username == 'unknown' and request and hasattr(request, 'POST'):
        post_data = request.POST
        username = post_data.get('login') or post_data.get('username') or post_data.get('email') or 'unknown'
        logger.debug(f"LOCKOUT DEBUG - Got username from POST: {username}")
    
    ip_address = _get_client_ip(request)
    
    # Log the lockout event (detailed for admin, not shown to user)
    logger.warning(
        f"AXES LOCKOUT RESPONSE: User '{username}' from IP {ip_address} - "
        f"Rendering inline lockout on login page"
    )
    
    # Create form with lockout state
    form = LockoutAwareLoginForm(
        initial={'login': username},
        request=request
    )
    
    # SECURITY: Generic message - don't reveal if it's username or IP block
    lockout_message = _(
        "Access has been temporarily restricted due to security reasons. Please contact administrator for assistance."
    )
    
    # Set lockout info on form
    form.set_lockout_info({
        'is_locked': True,
        'message': lockout_message,
        'locked_at': timezone.now(),
        'username': username,
    })
    
    # Add error to form for display
    form.add_lockout_error(lockout_message)
    
    # Prepare context - SECURITY: Don't expose cooloff_minutes to template
    context = {
        'form': form,
        'is_locked_out': True,
        'lockout_username': username,
        'lockout_message': lockout_message,
        # SECURITY: Don't expose these to user
        # 'cooloff_minutes': cooloff_minutes,  # Removed for security
        # 'lockout_timestamp': timezone.now().isoformat(),  # Removed for security
    }
    
    # Trigger async alert if configured
    _send_lockout_alert_async(username, ip_address)
    
    return render(
        request,
        'account/login.html',
        context,
        status=403  # Forbidden - important for security headers
    )


def _get_username_from_credentials(credentials: Dict[str, Any]) -> str:
    """
    Extract username from credentials dict.
    
    Axes may pass credentials in different formats depending on configuration.
    """
    if not credentials:
        return 'unknown'
    
    # Try various keys
    for key in ['username', 'login', 'email']:
        value = credentials.get(key)
        if value:
            return str(value)
    
    return 'unknown'


def _get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request."""
    if request is None:
        return 'unknown'
    
    if hasattr(request, 'axes_ip_address') and request.axes_ip_address:
        return request.axes_ip_address
    
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    
    return request.META.get('REMOTE_ADDR') or 'unknown'


def _send_lockout_alert_async(username: str, ip_address: str) -> None:
    """
    Send async alert for lockout event.
    Uses Celery if available and broker is running, otherwise logs only.
    """
    from django.conf import settings
    
    # Skip if in DEBUG mode or Celery not configured
    if settings.DEBUG:
        logger.debug(f"DEBUG mode - skipping Celery alert for lockout: {username}")
        return
    
    try:
        from backends.tenancy.tasks import send_security_alert
        from kombu.exceptions import OperationalError
        
        try:
            send_security_alert.delay(
                alert_type='user_lockout_inline',
                details={
                    'username': username,
                    'ip_address': ip_address,
                    'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'handler': 'inline_lockout_response',
                }
            )
            logger.debug(f"Queued lockout alert for {username}")
        except OperationalError as e:
            # Redis/broker not available - just log it
            logger.debug(f"Broker unavailable, skipping alert: {e}")
        
    except ImportError:
        logger.debug("Celery tasks not available - skipping async alert")
    except Exception as e:
        logger.debug(f"Failed to queue lockout alert (non-critical): {e}")


# =============================================================================
# ALTERNATIVE LOCKOUT RESPONSES
# =============================================================================

def json_lockout_response(
    request: HttpRequest,
    credentials: Dict[str, Any],
    *args,
    **kwargs
) -> HttpResponse:
    """
    JSON lockout response for API endpoints.
    Use this with: AXES_LOCKOUT_CALLABLE = 'backends.api.base.account.lockout.json_lockout_response'
    """
    from django.http import JsonResponse
    
    username = _get_username_from_credentials(credentials)
    
    logger.warning(f"AXES JSON LOCKOUT: User '{username}' from {_get_client_ip(request)}")
    
    return JsonResponse({
        'error': 'account_locked',
        'message': 'Account locked due to multiple failed login attempts. Please contact administrator.',
    }, status=403)
