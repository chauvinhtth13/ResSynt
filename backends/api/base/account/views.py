# backends/api/base/account/views.py
"""
Secure authentication views with django-axes integration.
"""
import logging
from typing import Any, Dict

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from allauth.account.views import LoginView
from axes.decorators import axes_dispatch
from axes.handlers.proxy import AxesProxyHandler
from axes.helpers import get_credentials

from .forms import AxesLoginForm
from ..utils import get_client_ip

logger = logging.getLogger(__name__)


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
@method_decorator(axes_dispatch, name='dispatch')
class SecureLoginView(LoginView):
    """
    Login view with axes brute-force protection.
    Uses PRG pattern to prevent form resubmission.
    """
    
    form_class = AxesLoginForm
    template_name = 'account/login.html'
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # Check PRG redirect errors from session first (fast path)
        login_errors = self.request.session.pop('login_errors', None)
        if login_errors:
            # Use cached session data instead of DB query
            context['is_locked_out'] = login_errors.get('is_locked', False)
            context['is_rate_limited'] = login_errors.get('is_rate_limited', False)
            context['prg_has_errors'] = login_errors.get('has_errors', False)
            context['prg_username'] = login_errors.get('username', '')
        else:
            # Fresh GET request - skip all expensive checks
            # Both axes lockout and rate limit will be checked on POST
            context['is_locked_out'] = False
            context['is_rate_limited'] = False
        
        return context
    
    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        login_errors = self.request.session.get('login_errors', {})
        if login_errors.get('username'):
            initial['login'] = login_errors['username']
        return initial
    
    def post(self, request, *args, **kwargs):
        """Check if locked or rate limited before processing."""
        # Check axes lockout first
        if AxesProxyHandler.is_locked(request):
            from .lockout import lockout_response
            return lockout_response(request, get_credentials(request))
        
        # Check rate limit (5/min)
        if self._is_rate_limited():
            self.request.session['login_errors'] = {
                'has_errors': False,
                'is_locked': False,
                'is_rate_limited': True,
                'username': request.POST.get('login', ''),
            }
            return HttpResponseRedirect(reverse('account_login'))
        
        return super().post(request, *args, **kwargs)
    
    def form_invalid(self, form: AxesLoginForm) -> HttpResponse:
        """PRG pattern with rate limiting."""
        login_value = form.data.get('login', '')
        is_locked = AxesProxyHandler.is_locked(self.request)
        
        # Check rate limit (5 attempts per minute)
        is_rate_limited = self._check_rate_limit()
        
        self.request.session['login_errors'] = {
            'has_errors': True,
            'is_locked': is_locked,
            'is_rate_limited': is_rate_limited,
            'username': login_value,
        }
        
        return HttpResponseRedirect(reverse('account_login'))
    
    def _check_rate_limit(self) -> bool:
        """
        Check and enforce rate limit: 5 attempts per minute per IP.
        Increments counter and returns True if rate limited.
        """
        from django.core.cache import cache
        
        ip = get_client_ip(self.request)
        cache_key = f"login_rate:{ip}"
        
        # Get current attempts in this minute
        attempts = cache.get(cache_key, 0)
        attempts += 1
        
        # Store with 60 second expiry
        cache.set(cache_key, attempts, 60)
        
        # Rate limit after 5 attempts
        return attempts > 5
    
    def _is_rate_limited(self) -> bool:
        """Check if currently rate limited (without incrementing)."""
        from django.core.cache import cache
        
        ip = get_client_ip(self.request)
        cache_key = f"login_rate:{ip}"
        attempts = cache.get(cache_key, 0)
        return attempts > 5
