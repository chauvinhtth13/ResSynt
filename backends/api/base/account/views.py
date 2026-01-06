# backends/api/base/account/views.py
"""
Secure authentication views with django-axes integration.

This module provides enhanced login views that:
1. Integrate properly with django-axes for brute force protection
2. Show remaining attempts before lockout
3. Handle lockout gracefully with inline errors
4. Include additional security measures (honeypot, rate limiting awareness)
5. Implement PRG (Post-Redirect-Get) pattern to prevent form resubmission
"""
import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import signals as auth_signals
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from allauth.account.views import LoginView
from axes.decorators import axes_dispatch, axes_form_invalid

from .forms import LockoutAwareLoginForm

logger = logging.getLogger(__name__)


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
@method_decorator(axes_dispatch, name='dispatch')
@method_decorator(axes_form_invalid, name='form_invalid')
class SecureLoginView(LoginView):
    """
    Enhanced login view with comprehensive security features.
    
    Security features:
    - django-axes integration for brute force protection
    - CSRF protection
    - Sensitive data protection in debug
    - Never cached
    - Remaining attempts display
    - Honeypot field for bot detection
    
    Axes integration:
    - axes_dispatch: Checks if user is locked before processing
    - axes_form_invalid: Tracks failed attempts when form is invalid
    """
    
    form_class = LockoutAwareLoginForm
    template_name = 'account/login.html'
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add request to form kwargs for lockout awareness."""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Add security-related context data.
        
        SECURITY: We only expose minimal lockout info to prevent
        attackers from gaining intelligence about the system.
        
        PRG Pattern: Retrieves error info from session if redirected.
        """
        context = super().get_context_data(**kwargs)
        
        # Check for PRG redirect errors in session
        login_errors = self.request.session.pop('login_errors', None)
        
        if login_errors:
            # Restore error state from session (PRG pattern)
            context.update({
                'is_locked_out': login_errors.get('is_locked', False),
                'prg_has_errors': login_errors.get('has_errors', False),
                'prg_username': login_errors.get('username', ''),
            })
        else:
            # Normal GET request - check lockout status
            lockout_info = self._get_lockout_info()
            context.update({
                'is_locked_out': lockout_info.get('is_locked', False),
            })
        
        return context
    
    def get_initial(self) -> Dict[str, Any]:
        """
        Provide initial form data.
        
        PRG Pattern: Restore username from session after redirect.
        """
        initial = super().get_initial()
        
        # Check if we have username from PRG redirect (peek, don't pop)
        login_errors = self.request.session.get('login_errors', {})
        if login_errors.get('username'):
            initial['login'] = login_errors.get('username', '')
        
        return initial
    
    def form_valid(self, form: LockoutAwareLoginForm) -> HttpResponse:
        """
        Handle successful form validation.
        
        Note: Actual authentication happens in parent class.
        This method adds logging and security tracking.
        """
        login_value = form.cleaned_data.get('login', 'unknown')
        logger.info(f"Login form valid for: {login_value}")
        
        return super().form_valid(form)
    
    def form_invalid(self, form: LockoutAwareLoginForm) -> HttpResponse:
        """
        Handle invalid form submission with PRG pattern.
        
        PRG (Post-Redirect-Get) Pattern:
        - Store error info in session
        - Redirect to GET to prevent form resubmission dialog on refresh
        - This prevents accidental login attempts when user refreshes
        
        Enhanced to:
        - Log failed attempts (internal only)
        - Track credentials for axes
        - Redirect to prevent resubmission
        
        SECURITY: We intentionally DON'T show remaining attempts to users
        to prevent attackers from knowing how close they are to lockout.
        """
        login_value = form.data.get('login', 'unknown')
        ip_address = self._get_client_ip()
        
        # Log for security monitoring (not shown to user)
        logger.warning(
            f"Login form invalid for '{login_value}' from {ip_address}"
        )
        
        # Get updated lockout info after this attempt (internal tracking only)
        lockout_info = self._get_lockout_info(username=login_value)
        
        # Store error info in session for PRG pattern
        self.request.session['login_errors'] = {
            'has_errors': True,
            'is_locked': lockout_info.get('is_locked', False),
            'username': login_value if not lockout_info.get('is_locked', False) else '',
        }
        
        # PRG Pattern: Redirect to prevent form resubmission on refresh
        # This eliminates "Confirm Form Resubmission" dialog
        return HttpResponseRedirect(reverse('account_login'))
    
    def _get_lockout_info(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current lockout status and remaining attempts.
        
        Args:
            username: Username to check (if not provided, extracts from request)
            
        Returns:
            Dict with lockout information
        """
        try:
            from axes.models import AccessAttempt
            from axes.conf import settings as axes_settings
            
            # Get username from form or request
            if not username:
                username = self.request.POST.get('login', '')
            
            if not username:
                return {'remaining_attempts': None, 'is_locked': False}
            
            # Get failure limit
            failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
            
            # Get current attempts
            attempt = AccessAttempt.objects.filter(
                username=username
            ).order_by('-attempt_time').first()
            
            if not attempt:
                return {
                    'remaining_attempts': failure_limit,
                    'is_locked': False,
                    'show_warning': False,
                }
            
            failures = attempt.failures_since_start
            remaining = max(0, failure_limit - failures)
            is_locked = failures >= failure_limit
            
            # Check cooloff
            if is_locked:
                cooloff = getattr(settings, 'AXES_COOLOFF_TIME', None)
                if cooloff:
                    cooloff_expiry = attempt.attempt_time + cooloff
                    if timezone.now() > cooloff_expiry:
                        # Cooloff expired
                        return {
                            'remaining_attempts': failure_limit,
                            'is_locked': False,
                            'show_warning': False,
                        }
            
            return {
                'remaining_attempts': remaining,
                'is_locked': is_locked,
                'show_warning': 0 < remaining <= 3,
                'failures': failures,
                'message': self._get_lockout_message() if is_locked else '',
            }
            
        except Exception as e:
            logger.error(f"Error getting lockout info: {e}")
            return {'remaining_attempts': None, 'is_locked': False}
    
    def _get_lockout_message(self) -> str:
        """Get user-friendly lockout message."""
        from django.utils.translation import gettext as _
        
        cooloff = getattr(settings, 'AXES_COOLOFF_TIME', None)
        if cooloff:
            minutes = int(cooloff.total_seconds() / 60)
            return _(
                "Your account has been temporarily locked. "
                "Please try again in %(minutes)d minutes."
            ) % {'minutes': minutes}
        
        return _(
            "Your account has been locked. "
            "Please contact support to unlock your account."
        )
    
    def _get_client_ip(self) -> str:
        """Get client IP address."""
        if hasattr(self.request, 'axes_ip_address'):
            return self.request.axes_ip_address
        
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        
        return self.request.META.get('REMOTE_ADDR', 'unknown')


# =============================================================================
# ADDITIONAL SECURE VIEWS
# =============================================================================

class SecureLogoutView:
    """
    Placeholder for custom logout view if needed.
    Currently allauth's logout is sufficient.
    """
    pass
