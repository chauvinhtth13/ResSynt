"""
Unified Tenancy Middleware.

Handles study routing, security headers, and performance monitoring.
"""
import logging
import re
import time
from typing import Callable, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import connection, connections
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from .db_loader import study_db_manager
from .db_router import set_current_db, clear_current_db
from .models import Study

logger = logging.getLogger(__name__)


class UnifiedTenancyMiddleware:
    """
    Middleware combining study routing, security, and monitoring.
    
    Features:
    - Study context management with caching
    - Security headers injection
    - Performance monitoring
    - Database connection management
    """
    
    # Session keys
    STUDY_ID_KEY = 'current_study'
    STUDY_CODE_KEY = 'current_study_code'
    STUDY_DB_KEY = 'current_study_db'
    
    # Cache settings
    CACHE_PREFIX = 'mw_'
    CACHE_TTL = 300  # 5 minutes
    
    # Performance thresholds
    SLOW_REQUEST_MS = 1000
    MAX_QUERIES = 100
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    }
    
    # Compiled regex patterns (class-level for reuse)
    _static_re = re.compile(r'^/(?:static|media|assets)/|^/favicon\.ico$', re.I)
    _public_re = re.compile(r'^/$|^/(?:accounts|password-reset|select-study)/', re.I)
    _auth_re = re.compile(r'^/(?:dashboard|data|reports|analytics|export|studies)/', re.I)
    _admin_re = re.compile(r'^/(?:admin|secret-admin)/', re.I)
    _study_path_re = re.compile(r'^/studies/(?P<code>[A-Za-z0-9_]+)(?:/|$)', re.I)
    _i18n_re = re.compile(r'^/(?:vi|en)/')
    
    # Valid study code pattern (security)
    _valid_code_re = re.compile(r'^[A-Z0-9_]{2,20}$')
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    # =========================================================================
    # Main Entry Point
    # =========================================================================
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request through middleware chain."""
        # Start timing
        request._start_time = time.time()
        
        if settings.DEBUG:
            request._queries_start = len(connection.queries)
        
        # Setup axes attributes
        self._setup_axes_attributes(request)
        
        # Normalize path
        path = self._normalize_path(request.path)
        
        # Fast path: static files
        if self._static_re.match(path):
            return self._handle_static(request)
        
        # Set default database context
        set_current_db('default')
        
        try:
            # Public paths
            if self._public_re.match(path):
                return self._process_request(request)
            
            # Check authentication
            if not request.user.is_authenticated:
                if self._auth_re.match(path):
                    return redirect(f"{reverse('account_login')}?next={request.path}")
                return self._process_request(request)
            
            # Check if account is active
            if not getattr(request.user, 'is_active', True):
                return HttpResponse('Account deactivated.', status=403)
            
            # Admin paths
            if self._admin_re.match(path):
                if not request.user.is_superuser:
                    raise Http404()
                return self._process_request(request)
            
            # Study paths
            if self._study_path_re.match(path) or self._auth_re.match(path):
                study = self._get_study_for_request(request, path)
                
                if not study:
                    return redirect('select_study')
                
                # Setup study context
                self._setup_study_context(request, study)
                set_current_db(study.db_name)
                study_db_manager.add_study_db(study.db_name)
            
            return self._process_request(request)
            
        finally:
            # Cleanup
            clear_current_db()
            self._cleanup_connections(request)
    
    # =========================================================================
    # Path Helpers
    # =========================================================================
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path by removing i18n prefix."""
        if not path:
            return '/'
        if not path.startswith('/'):
            path = '/' + path
        return self._i18n_re.sub('/', path)
    
    def _extract_study_code(self, path: str) -> Optional[str]:
        """Extract and validate study code from path."""
        match = self._study_path_re.match(self._normalize_path(path))
        if not match:
            return None
        
        code = match.group('code').upper()
        
        # Security: validate code format
        if not self._valid_code_re.match(code):
            logger.warning(f"Invalid study code format: {code[:50]}")
            return None
        
        return code
    
    # =========================================================================
    # Axes Integration
    # =========================================================================
    
    def _setup_axes_attributes(self, request: HttpRequest) -> None:
        """Setup attributes required by django-axes."""
        if not hasattr(request, 'axes_attempt_time'):
            request.axes_attempt_time = time.time()
        
        if not hasattr(request, 'axes_ip_address'):
            request.axes_ip_address = self._get_client_ip(request)
        
        if not hasattr(request, 'axes_user_agent'):
            request.axes_user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        
        if not hasattr(request, 'axes_path_info'):
            request.axes_path_info = request.META.get('PATH_INFO', '')[:255]
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Get client IP address securely.
        
        Note: X-Forwarded-For can be spoofed. In production, configure
        AXES_IPWARE_PROXY_COUNT based on your proxy setup.
        """
        # Use first IP from X-Forwarded-For if behind proxy
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            # Take only the first IP (client IP when properly configured)
            return xff.split(',')[0].strip()[:45]
        
        return request.META.get('REMOTE_ADDR', '127.0.0.1')[:45]
    
    # =========================================================================
    # Study Context
    # =========================================================================
    
    def _get_study_for_request(self, request: HttpRequest, path: str) -> Optional[Study]:
        """Get study from URL or session."""
        # Try URL first
        code = self._extract_study_code(path)
        if code:
            study = self._get_study_by_code(request, code)
            if study:
                self._update_session(request, study)
                return study
        
        # Fall back to session
        return self._get_study_from_session(request)
    
    def _get_study_by_code(self, request: HttpRequest, code: str) -> Optional[Study]:
        """Get study by code with caching."""
        cache_key = f"{self.CACHE_PREFIX}study_{code}_{request.user.pk}"
        study = cache.get(cache_key)
        
        if study is not None:
            return study
        
        try:
            study = Study.objects.select_related('created_by').get(
                code=code,
                memberships__user=request.user,
                memberships__is_active=True,
                status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
            )
            
            # Ensure database is registered
            if study.db_name not in connections.databases:
                study_db_manager.add_study_db(study.db_name)
            
            cache.set(cache_key, study, self.CACHE_TTL)
            return study
            
        except Study.DoesNotExist:
            logger.debug(f"Study {code} not accessible by user {request.user.pk}")
            return None
        except Exception as e:
            logger.error(f"Error loading study {code}: {type(e).__name__}")
            return None
    
    def _get_study_from_session(self, request: HttpRequest) -> Optional[Study]:
        """Get study from session with caching."""
        # Request-level cache
        if hasattr(request, '_study_cache'):
            return request._study_cache
        
        study_id = request.session.get(self.STUDY_ID_KEY)
        if not study_id:
            return None
        
        # Django cache
        cache_key = f"{self.CACHE_PREFIX}study_id_{study_id}_{request.user.pk}"
        study = cache.get(cache_key)
        
        if study is None:
            try:
                study = Study.objects.select_related('created_by').get(
                    id=study_id,
                    memberships__user=request.user,
                    memberships__is_active=True,
                    status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
                )
                
                if study.db_name not in connections.databases:
                    study_db_manager.add_study_db(study.db_name)
                
                cache.set(cache_key, study, self.CACHE_TTL)
                
            except Study.DoesNotExist:
                # Clear invalid session
                self._clear_session_study(request)
                return None
            except Exception as e:
                logger.error(f"Error loading study {study_id}: {type(e).__name__}")
                return None
        
        request._study_cache = study
        return study
    
    def _update_session(self, request: HttpRequest, study: Study) -> None:
        """Update session with study info."""
        request.session[self.STUDY_ID_KEY] = study.pk
        request.session[self.STUDY_CODE_KEY] = study.code
        request.session[self.STUDY_DB_KEY] = study.db_name
        request.session.modified = True
    
    def _clear_session_study(self, request: HttpRequest) -> None:
        """Clear study from session."""
        for key in (self.STUDY_ID_KEY, self.STUDY_CODE_KEY, self.STUDY_DB_KEY):
            request.session.pop(key, None)
    
    def _setup_study_context(self, request: HttpRequest, study: Study) -> None:
        """Setup study context on request."""
        request.study = study
        request.study_code = study.code
        request.study_id = study.pk
        request.study_db = study.db_name
        
        # Lazy load permissions
        from .utils import TenancyUtils
        request.study_permissions = SimpleLazyObject(
            lambda: TenancyUtils.get_user_permissions(request.user, study)
        )
        request.study_sites = SimpleLazyObject(
            lambda: TenancyUtils.get_user_sites(request.user, study)
        )
        
        # Track access
        TenancyUtils.track_study_access(request.user, study)
    
    # =========================================================================
    # Request Processing
    # =========================================================================
    
    def _handle_static(self, request: HttpRequest) -> HttpResponse:
        """Handle static file requests."""
        response = self.get_response(request)
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        response['Vary'] = 'Accept-Encoding'
        return response
    
    def _process_request(self, request: HttpRequest) -> HttpResponse:
        """Process request and add headers."""
        response = self.get_response(request)
        
        self._add_performance_headers(request, response)
        self._add_security_headers(response)
        self._add_cache_headers(request, response)
        
        return response
    
    def _add_performance_headers(self, request: HttpRequest, response: HttpResponse) -> None:
        """Add performance metrics to response."""
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000
            response['X-Response-Time'] = f"{duration_ms:.2f}ms"
            
            if duration_ms > self.SLOW_REQUEST_MS:
                logger.warning(f"Slow request: {request.method} {request.path} ({duration_ms:.0f}ms)")
        
        if settings.DEBUG and hasattr(request, '_queries_start'):
            query_count = len(connection.queries) - request._queries_start
            response['X-DB-Queries'] = str(query_count)
            
            if query_count > self.MAX_QUERIES:
                logger.warning(f"Excessive queries: {request.path} ({query_count} queries)")
    
    def _add_security_headers(self, response: HttpResponse) -> None:
        """Add security headers."""
        for header, value in self.SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value
    
    def _add_cache_headers(self, request: HttpRequest, response: HttpResponse) -> None:
        """Add cache control headers."""
        if 'Cache-Control' in response:
            return
        
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
        else:
            response['Cache-Control'] = 'public, max-age=300'
            response['Vary'] = 'Cookie, Accept-Encoding'
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def _cleanup_connections(self, request: HttpRequest) -> None:
        """Cleanup database connections."""
        study = getattr(request, 'study', None)
        if not study:
            return
        
        try:
            if study.db_name in connections.databases:
                conn = connections[study.db_name]
                conn.close_if_unusable_or_obsolete()
        except Exception as e:
            logger.debug(f"Connection cleanup error: {type(e).__name__}")


# =============================================================================
# Helper Functions
# =============================================================================

def switch_study_context(request: HttpRequest, study_code: str) -> bool:
    """
    Manually switch study context.
    
    Args:
        request: HTTP request
        study_code: Study code to switch to
        
    Returns:
        True if successful
    """
    try:
        study = Study.objects.select_related('created_by').get(
            code=study_code.upper(),
            memberships__user=request.user,
            memberships__is_active=True,
            status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
        )
        
        # Update session
        request.session['current_study'] = study.pk
        request.session['current_study_code'] = study.code
        request.session['current_study_db'] = study.db_name
        
        # Setup context
        request.study = study
        request.study_code = study.code
        request.study_id = study.pk
        request.study_db = study.db_name
        
        # Switch database
        set_current_db(study.db_name)
        study_db_manager.add_study_db(study.db_name)
        
        return True
        
    except Study.DoesNotExist:
        return False
    except Exception as e:
        logger.error(f"Error switching study: {type(e).__name__}")
        return False


class BlockSignupMiddleware:
    """Block access to signup page."""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == '/accounts/signup/':
            raise Http404()
        return self.get_response(request)