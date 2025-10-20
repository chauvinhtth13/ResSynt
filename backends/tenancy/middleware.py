# backends/tenancy/middleware.py
"""
Unified Tenancy Middleware - Simplified Version
Handles: performance tracking, security headers, study context
WITHOUT TenantContext class
"""
import logging
import time
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger(__name__)


class UnifiedTenancyMiddleware:
    """
    Simplified middleware for:
    - Performance tracking
    - Security headers
    - Cache control
    - Study context management via session
    """
    
    # Public URLs that don't require authentication or study context
    PUBLIC_URLS = [
        '/',
        '/login/',
        '/logout/',
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def __init__(self, get_response):
        """Initialize middleware"""
        self.get_response = get_response
        logger.debug("UnifiedTenancyMiddleware initialized")
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Main middleware entry point
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response (guaranteed not None)
        """
        # Start performance tracking
        setattr(request, '_start_time', time.time())
        
        # Log request (debug mode only)
        if settings.DEBUG:
            logger.debug(f"Request: {request.method} {request.path}")
        
        try:
            # Process request
            response = self._process_request(request)
            
            # Ensure response is never None
            if response is None:
                from django.http import HttpResponse
                logger.error(
                    f"View returned None for: {request.method} {request.path} "
                    f"(user: {request.user})"
                )
                response = HttpResponse(
                    "Internal Server Error: View did not return a response",
                    status=500
                )
            
            return response
            
        except Exception as e:
            logger.exception(f"Error in middleware: {e}")
            # Return error response instead of crashing
            return HttpResponse(f"Internal Server Error: {str(e)}", status=500)
    
    def _process_request(self, request: HttpRequest) -> HttpResponse:
        """
        Process request and add middleware features
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response
        """
        # Check if study context is needed
        if self._needs_study_context(request):
            self._setup_study_context(request)
        
        # Get response from next middleware/view
        response = self.get_response(request)
        
        # Add headers (with error handling)
        if response is not None:
            try:
                self._add_performance_metrics(request, response)
                self._add_security_headers(request, response)
                self._add_cache_headers(request, response)
            except Exception as e:
                logger.error(f"Error adding headers: {e}")
        
        return response
    
    def _needs_study_context(self, request: HttpRequest) -> bool:
        """
        Check if request needs study context
        
        Args:
            request: HTTP request
            
        Returns:
            True if study context needed
        """
        # Skip for public URLs
        if self._is_public_url(request.path):
            return False
        
        # Skip for unauthenticated users
        if not request.user.is_authenticated:
            return False
        
        # Skip for superuser accessing admin
        if request.user.is_superuser and request.path.startswith('/admin/'):
            return False
        
        # Need study context for authenticated non-admin users
        return True
    
    def _setup_study_context(self, request: HttpRequest):
        """
        Setup study context from session
        
        Args:
            request: HTTP request
        """
        try:
            # Get study ID from session
            study_id = request.session.get('current_study_id')
            
            if study_id:
                # Set study context on request (use setattr to avoid static type checker errors)
                setattr(request, 'study_id', study_id)
                
                # Optional: Load full study object if needed
                # from backends.tenancy.models import Study
                # request.study = Study.objects.get(pk=study_id)
                
                logger.debug(f"Study context set: {study_id}")
            else:
                logger.debug("No study context in session")
                
        except Exception as e:
            logger.error(f"Error setting up study context: {e}")
    
    def _add_performance_metrics(self, request: HttpRequest, response: HttpResponse):
        """
        Add performance metrics to response headers
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        if response is None:
            return
        
        try:
            start_time = getattr(request, '_start_time', None)
            if start_time:
                duration_ms = (time.time() - start_time) * 1000
                response['X-Response-Time'] = f"{duration_ms:.2f}ms"
                
                # Log slow requests
                threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1000)
                if duration_ms > threshold:
                    logger.warning(
                        f"Slow request: {request.method} {request.path} "
                        f"took {duration_ms:.2f}ms"
                    )
        except Exception as e:
            logger.error(f"Error adding performance metrics: {e}")
    
    def _add_security_headers(self, request: HttpRequest, response: HttpResponse):
        """
        Add security headers to response
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        if response is None:
            return
        
        try:
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
            }
            
            for header, value in security_headers.items():
                if not response.has_header(header):
                    response[header] = value
                    
        except Exception as e:
            logger.error(f"Error adding security headers: {e}")
    
    def _add_cache_headers(self, request: HttpRequest, response: HttpResponse):
        """
        Add cache control headers
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        if response is None:
            return
        
        try:
            # Don't override existing Cache-Control
            if response.has_header('Cache-Control'):
                return
            
            # Default: no cache for dynamic content
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        except Exception as e:
            logger.error(f"Error adding cache headers: {e}")
    
    def _is_public_url(self, path: str) -> bool:
        """
        Check if URL is public (doesn't require study context)
        
        Args:
            path: URL path
            
        Returns:
            True if public URL
        """
        return any(path.startswith(public_url) for public_url in self.PUBLIC_URLS)


class AxesNoRedirectMiddleware:
    """
    Middleware to catch Axes lockout and render on login page
    FIXED: Always returns response
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("AxesNoRedirectMiddleware initialized")
    
    def __call__(self, request):
        """Process request and catch Axes exceptions"""
        from axes.exceptions import AxesBackendPermissionDenied
        
        try:
            # Get response from view
            response = self.get_response(request)
            
            # CRITICAL: Check if response is None
            if response is None:
                self.logger.error(f"AxesNoRedirectMiddleware: get_response returned None for {request.path}")
                from django.http import HttpResponse
                response = HttpResponse("Error: View returned None", status=500)
            
            return response
            
        except AxesBackendPermissionDenied as e:
            # Axes raised lockout exception
            self.logger.warning(
                f"AxesBackendPermissionDenied caught: {e} "
                f"(path: {request.path}, method: {request.method})"
            )
            
            # Only handle for login paths
            if self._is_login_path(request.path):
                response = self._render_lockout_page(request)
                
                # CRITICAL: Check response before returning
                if response is None:
                    self.logger.error("_render_lockout_page returned None!")
                    from django.http import HttpResponse
                    response = HttpResponse("Lockout page error", status=500)
                
                return response
            
            # For other paths, re-raise
            raise
        
        except Exception as e:
            self.logger.error(f"Unexpected exception in AxesNoRedirectMiddleware: {e}", exc_info=True)
            from django.http import HttpResponse
            return HttpResponse(f"Middleware error: {e}", status=500)
    
    def process_exception(self, request, exception):
        """Backup exception handler"""
        from axes.exceptions import AxesBackendPermissionDenied
        
        if isinstance(exception, AxesBackendPermissionDenied):
            self.logger.warning(
                f"AxesBackendPermissionDenied in process_exception: {exception}"
            )
            
            if self._is_login_path(request.path):
                response = self._render_lockout_page(request)
                
                # CRITICAL: Check response
                if response is None:
                    self.logger.error("process_exception: _render_lockout_page returned None!")
                    from django.http import HttpResponse
                    response = HttpResponse("Lockout error", status=500)
                
                return response
        
        return None
    
    def _is_login_path(self, path: str) -> bool:
        """Check if path is login-related"""
        login_paths = ['/', '/login/', '/login', '/accounts/login/', '/accounts/login']
        return path in login_paths
    
    def _render_lockout_page(self, request):
        """
        Render login page with lockout state
        GUARANTEED to return HttpResponse
        """
        try:
            from django.shortcuts import render
            from backends.api.base.constants import LoginMessages
            from backends.api.base.login import UsernameOrEmailAuthenticationForm
            
            # Get username from POST if available
            username_input = request.POST.get('username', '') if request.method == 'POST' else ''
            
            # Create form
            form = UsernameOrEmailAuthenticationForm(request)
            if username_input:
                form.initial['username'] = username_input
            
            # Build context
            context = {
                'form': form,
                'error_message': LoginMessages.ACCOUNT_LOCKED,
                'form_disabled': True,
                'is_locked': True,
                'LANGUAGE_CODE': 'vi'
            }
            
            # Render with 403 status
            response = render(request, 'authentication/login.html', context)
            response.status_code = 403
            
            self.logger.info(f"Rendered lockout page for: {request.path}")
            
            # CRITICAL: Ensure we return response
            if response is None:
                self.logger.error("render() returned None!")
                from django.http import HttpResponse
                return HttpResponse("Render failed", status=500)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error rendering lockout page: {e}", exc_info=True)
            from django.http import HttpResponse
            return HttpResponse(
                f"<h1>Account Locked</h1><p>Error: {e}</p>",
                status=403
            )