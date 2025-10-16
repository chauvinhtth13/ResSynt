# backend/tenancy/middleware.py - COMPLETE OPTIMIZED VERSION
"""
Unified Tenancy Middleware
Handles study routing, security, performance monitoring, and database management
"""
import logging
import time
import re
from typing import Optional, Callable

from django.http import HttpRequest, HttpResponse, Http404
from django.conf import settings
from django.core.cache import cache
from django.utils.functional import SimpleLazyObject
from django.shortcuts import redirect
from django.urls import reverse
from django.db import connection, connections

from .models import Study
from .db_loader import study_db_manager
from .db_router import set_current_db
from .utils import TenancyUtils

logger = logging.getLogger(__name__)


class UnifiedTenancyMiddleware:
    """
    Unified middleware combining:
    - Study routing and context management
    - Security headers
    - Performance monitoring
    - Cache control
    - Database connection management
    """
    
    # ==========================================
    # SESSION KEYS
    # ==========================================
    STUDY_ID_KEY = 'current_study'
    STUDY_CODE_KEY = 'current_study_code'
    STUDY_DB_KEY = 'current_study_db'
    
    # ==========================================
    # CACHE SETTINGS
    # ==========================================
    CACHE_PREFIX = 'mw_'
    CACHE_TTL = 300  # 5 minutes
    
    # ==========================================
    # PERFORMANCE THRESHOLDS
    # ==========================================
    SLOW_REQUEST_MS = 1000  # Log requests slower than 1 second
    MAX_QUERIES = 100       # Warn if more than 100 queries
    
    # ==========================================
    # SECURITY HEADERS
    # ==========================================
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    }
    
    def __init__(self, get_response: Callable):
        """
        Initialize middleware
        
        Args:
            get_response: Next middleware or view in chain
        """
        self.get_response = get_response
        self._compile_path_matchers()
        
        logger.debug("UnifiedTenancyMiddleware initialized")
    
    # ==========================================
    # PATH MATCHING (Pre-compiled for Performance)
    # ==========================================
    
    def _compile_path_matchers(self):
        """
        Pre-compile all regex patterns for path matching
        This is done once at startup for optimal performance
        """
        # Static files pattern
        self._static_re = re.compile(
            r'^/(?:static|media|assets)/|^/favicon\.ico$',
            re.IGNORECASE
        )
        
        # Public paths (no authentication required)
        self._public_re = re.compile(
            r'^/$|^/(?:login|logout|password-reset|select-study)/',
            re.IGNORECASE
        )
        
        # Paths requiring authentication
        self._auth_re = re.compile(
            r'^/(?:dashboard|data|reports|analytics|export|studies)/',
            re.IGNORECASE
        )
        
        # Admin paths
        self._admin_re = re.compile(
            r'^/(?:admin|secret-admin)/',
            re.IGNORECASE
        )
        
        # Study-specific path with code extraction
        self._study_path_re = re.compile(
            r'^/studies/(?P<study_code>[A-Z0-9_]+)(?:/|$)',
            re.IGNORECASE
        )
        
        # Internationalization prefix pattern
        self._i18n_prefix_re = re.compile(r'^/(?:vi|en)/')
        
        # Create path normalizer
        def normalize_path(path: str) -> str:
            """Normalize path by removing i18n prefix and ensuring leading slash"""
            if not path:
                return '/'
            
            # Ensure leading slash
            if not path.startswith('/'):
                path = '/' + path
            
            # Remove i18n prefix
            path = self._i18n_prefix_re.sub('/', path)
            
            # Ensure starts with /
            if not path.startswith('/'):
                path = '/' + path
            
            return path
        
        self._normalize_path = normalize_path
        
        # Create fast matcher functions
        self.is_static = lambda path: bool(self._static_re.match(self._normalize_path(path)))
        self.is_public = lambda path: bool(self._public_re.match(self._normalize_path(path)))
        self.needs_auth = lambda path: bool(self._auth_re.match(self._normalize_path(path)))
        self.is_admin = lambda path: bool(self._admin_re.match(self._normalize_path(path)))
        self.is_study_path = lambda path: bool(self._study_path_re.match(self._normalize_path(path)))
        
        def extract_study_code(path: str) -> Optional[str]:
            """Extract study code from URL path"""
            normalized = self._normalize_path(path)
            match = self._study_path_re.match(normalized)
            return match.group('study_code').upper() if match else None
        
        self.extract_study_code = extract_study_code
        
        logger.debug("Path matchers compiled successfully")
    
    # ==========================================
    # MAIN MIDDLEWARE ENTRY POINT
    # ==========================================
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Main middleware processing
        
        Args:
            request: Django HTTP request
            
        Returns:
            HTTP response
        """
        # Start performance tracking
        request._start_time = time.time()
        request._middleware_processed = True
        
        if settings.DEBUG:
            request._queries_start = len(connection.queries)
        
        # Log request start
        self._log_request_start(request)
        
        # Fast path for static files
        if self.is_static(request.path):
            return self._handle_static_request(request)
        
        # Set default database context
        set_current_db('default')
        
        # Handle public paths (no auth required)
        if self.is_public(request.path):
            return self._process_request(request)
        
        # Check authentication
        if not request.user.is_authenticated:
            if self.needs_auth(request.path):
                return redirect(f"{reverse('login')}?next={request.path}")
            return self._process_request(request)
        
        # Handle admin paths (superuser only)
        if self.is_admin(request.path):
            if not request.user.is_superuser:
                raise Http404("Page not found")
            return self._process_request(request)
        
        # Handle study-specific paths or paths requiring study context
        if self.is_study_path(request.path) or self.needs_auth(request.path):
            study = self._get_study_for_request(request)
            
            if not study:
                logger.warning(f"No study context for authenticated path: {request.path}")
                return redirect('select_study')
            
            # Setup study context
            self._setup_study_context(request, study)
            
            # Switch to study database
            logger.debug(f"Switching to database: {study.db_name}")
            set_current_db(study.db_name)
            study_db_manager.add_study_db(study.db_name)
        
        # Process request with cleanup
        try:
            response = self._process_request(request)
        finally:
            # Always cleanup
            set_current_db('default')
            self._cleanup_connections(request)
        
        return response
    
    # ==========================================
    # REQUEST HANDLERS
    # ==========================================
    
    def _handle_static_request(self, request: HttpRequest) -> HttpResponse:
        """
        Handle static file requests with aggressive caching
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with cache headers
        """
        response = self.get_response(request)
        
        # Aggressive caching for static files
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        response['Vary'] = 'Accept-Encoding'
        
        return response
    
    def _process_request(self, request: HttpRequest) -> HttpResponse:
        """
        Process request with all middleware features
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with headers and metrics
        """
        # Get response from next middleware/view
        response = self.get_response(request)
        
        # Add performance metrics
        self._add_performance_metrics(request, response)
        
        # Add security headers
        self._add_security_headers(request, response)
        
        # Add cache control headers
        self._add_cache_headers(request, response)
        
        return response
    
    # ==========================================
    # STUDY CONTEXT MANAGEMENT
    # ==========================================
    
    def _get_study_for_request(self, request: HttpRequest) -> Optional[Study]:
        """
        Get study for current request with multiple strategies:
        1. Extract from URL path
        2. Get from session
        3. Return None if not found
        
        Args:
            request: HTTP request
            
        Returns:
            Study instance or None
        """
        # Strategy 1: Extract study code from URL
        study_code = self.extract_study_code(request.path)
        
        if study_code:
            study = self._get_study_by_code(request, study_code)
            if study:
                # Update session with new study
                self._update_session_study(request, study)
                return study
        
        # Strategy 2: Get from session
        study = self._get_study_from_session(request)
        if study:
            return study
        
        # No study found
        logger.warning(
            f"No study context found for user {request.user.pk} "
            f"on path {request.path}"
        )
        return None
    
    def _get_study_by_code(self, request: HttpRequest, study_code: str) -> Optional[Study]:
        """
        Get study by code from URL
        
        Args:
            request: HTTP request
            study_code: Study code from URL
            
        Returns:
            Study instance or None
        """
        cache_key = f"{self.CACHE_PREFIX}study_code_{study_code}_{request.user.pk}"
        study = cache.get(cache_key)
        
        if study is None:
            try:
                study = Study.objects.select_related('created_by').get(
                    code=study_code.upper(),
                    memberships__user=request.user,
                    memberships__is_active=True,
                    status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
                )
                
                # Verify database exists
                if study.db_name not in connections.databases:
                    logger.debug(f"Registering database: {study.db_name}")
                    study_db_manager.add_study_db(study.db_name)
                
                # Cache for 5 minutes
                cache.set(cache_key, study, self.CACHE_TTL)
                
                logger.debug(f"Study {study_code} loaded from URL for user {request.user.pk}")
                
            except Study.DoesNotExist:
                logger.error(
                    f"Study {study_code} not found or not accessible "
                    f"by user {request.user.pk}"
                )
                return None
            except Exception as e:
                logger.error(f"Error loading study {study_code}: {e}", exc_info=True)
                return None
        
        return study
    
    def _get_study_from_session(self, request: HttpRequest) -> Optional[Study]:
        """
        Get study from session with triple-layer caching
        
        Args:
            request: HTTP request
            
        Returns:
            Study instance or None
        """
        # Layer 1: Request-level cache (fastest)
        if hasattr(request, '_study_cache'):
            return request._study_cache
        
        # Get study ID from session
        study_id = request.session.get(self.STUDY_ID_KEY)
        if not study_id:
            return None
        
        # Layer 2: Django cache
        cache_key = f"{self.CACHE_PREFIX}study_{study_id}_{request.user.pk}"
        study = cache.get(cache_key)
        
        if study is None:
            # Layer 3: Database query
            try:
                study = Study.objects.select_related('created_by').get(
                    id=study_id,
                    memberships__user=request.user,
                    memberships__is_active=True,
                    status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
                )
                
                # Verify database exists
                if study.db_name not in connections.databases:
                    logger.debug(f"Registering database: {study.db_name}")
                    study_db_manager.add_study_db(study.db_name)
                
                # Cache for future requests
                cache.set(cache_key, study, self.CACHE_TTL)
                
            except Study.DoesNotExist:
                logger.error(
                    f"Study {study_id} from session not accessible "
                    f"by user {request.user.pk}"
                )
                # Clear invalid session
                request.session.pop(self.STUDY_ID_KEY, None)
                request.session.pop(self.STUDY_CODE_KEY, None)
                request.session.pop(self.STUDY_DB_KEY, None)
                return None
            except Exception as e:
                logger.error(f"Error loading study {study_id}: {e}", exc_info=True)
                return None
        
        # Store in request cache
        request._study_cache = study
        return study
    
    def _update_session_study(self, request: HttpRequest, study: Study):
        """
        Update session with study information
        
        Args:
            request: HTTP request
            study: Study instance
        """
        request.session[self.STUDY_ID_KEY] = study.pk
        request.session[self.STUDY_CODE_KEY] = study.code
        request.session[self.STUDY_DB_KEY] = study.db_name
        request.session.modified = True
        
        logger.debug(f"Session updated with study {study.code}")
    
    def _setup_study_context(self, request: HttpRequest, study: Study):
        """
        Setup study context on request object with lazy loading
        
        Args:
            request: HTTP request
            study: Study instance
        """
        # Set basic study info
        request.study = study
        request.study_code = study.code
        request.study_id = study.pk
        request.study_db = study.db_name
        
        # Lazy load permissions (only loaded when accessed)
        request.study_permissions = SimpleLazyObject(
            lambda: TenancyUtils.get_user_permissions(request.user, study)
        )
        
        # Lazy load sites (only loaded when accessed)
        request.study_sites = SimpleLazyObject(
            lambda: TenancyUtils.get_user_sites(request.user, study)
        )
        
        # Track access (throttled to avoid excessive updates)
        TenancyUtils.track_study_access(request.user, study)
        
        logger.debug(f"Study context setup: {study.code} for user {request.user.pk}")
    
    # ==========================================
    # RESPONSE ENHANCEMENTS
    # ==========================================
    
    def _add_performance_metrics(self, request: HttpRequest, response: HttpResponse):
        """
        Add performance metrics to response headers
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000
            response['X-Response-Time'] = f"{duration_ms:.2f}ms"
            
            # Log slow requests
            if duration_ms > self.SLOW_REQUEST_MS:
                logger.warning(
                    f"SLOW REQUEST: {request.method} {request.path} "
                    f"took {duration_ms:.2f}ms"
                )
        
        # Add query count in DEBUG mode
        if settings.DEBUG and hasattr(request, '_queries_start'):
            query_count = len(connection.queries) - request._queries_start
            response['X-DB-Queries'] = str(query_count)
            
            # Warn about excessive queries
            if query_count > self.MAX_QUERIES:
                logger.warning(
                    f"EXCESSIVE QUERIES: {request.path} "
                    f"executed {query_count} queries"
                )
    
    def _add_security_headers(self, request: HttpRequest, response: HttpResponse):
        """
        Add security headers to response
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        # Add standard security headers
        for header, value in self.SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value
        
        # Add HSTS for HTTPS connections
        if request.is_secure():
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )
    
    def _add_cache_headers(self, request: HttpRequest, response: HttpResponse):
        """
        Add appropriate cache control headers
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        # Skip if cache headers already set
        if 'Cache-Control' in response:
            return
        
        # Static files - cache forever
        if self.is_static(request.path):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Vary'] = 'Accept-Encoding'
        
        # Authenticated users - no cache
        elif request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Anonymous users - short cache
        else:
            response['Cache-Control'] = 'public, max-age=300'
            response['Vary'] = 'Cookie, Accept-Encoding'
    
    # ==========================================
    # CLEANUP
    # ==========================================
    
    def _cleanup_connections(self, request: HttpRequest):
        """
        Cleanup database connections after request
        FIXED: Properly check connection existence
        
        Args:
            request: HTTP request
        """
        study = getattr(request, 'study', None)
        
        if study and study.db_name in connections.databases:
            try:
                #  FIXED: Proper way to get connection
                conn_wrapper = connections[study.db_name]
                
                # Check if connection is actually open
                if hasattr(conn_wrapper, 'connection') and conn_wrapper.connection is not None:
                    should_close = False
                    
                    # Check if too many queries
                    if hasattr(conn_wrapper, 'queries') and len(conn_wrapper.queries) > 100:
                        should_close = True
                        logger.debug(f"Closing {study.db_name}: too many queries")
                    
                    # Check if unusable
                    if not conn_wrapper.is_usable():
                        should_close = True
                        logger.debug(f"Closing {study.db_name}: connection unusable")
                    
                    if should_close:
                        conn_wrapper.close()
                        
            except Exception as e:
                logger.error(f"Error cleaning connection {study.db_name}: {e}")
        
        # Check all study connections
        try:
            for alias in list(connections.databases.keys()):
                if alias != 'default' and alias.startswith(settings.STUDY_DB_PREFIX):
                    try:
                        conn_wrapper = connections[alias]
                        
                        # Use Django's built-in method
                        conn_wrapper.close_if_unusable_or_obsolete()
                        
                    except Exception as e:
                        logger.error(f"Error checking connection {alias}: {e}")
        except Exception as e:
            logger.error(f"Error in connection cleanup: {e}")
    
    # ==========================================
    # LOGGING
    # ==========================================
    
    def _log_request_start(self, request: HttpRequest):
        """
        Log request start information
        
        Args:
            request: HTTP request
        """
        if not settings.DEBUG:
            return
        
        try:
            user_id = request.user.pk if hasattr(request, 'user') and request.user.is_authenticated else None
            study_session = request.session.get(self.STUDY_ID_KEY) if hasattr(request, 'session') else None
            
            logger.debug(
                f"REQUEST START: {request.method} {request.path} | "
                f"User: {user_id} | "
                f"Auth: {getattr(request.user, 'is_authenticated', False)} | "
                f"Study Session: {study_session}"
            )
        except Exception as e:
            logger.error(f"Error logging request start: {e}")


# ==========================================
# HELPER FUNCTION FOR MANUAL STUDY SWITCHING
# ==========================================

def switch_study_context(request: HttpRequest, study_code: str) -> bool:
    """
    Manually switch study context for a request
    Useful in views or APIs
    
    Args:
        request: HTTP request
        study_code: Study code to switch to
        
    Returns:
        True if successful, False otherwise
    
    Example:
        if switch_study_context(request, '43EN'):
            # Now working in study 43EN context
            patients = Patient.objects.all()
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
        
        logger.debug(f"Manually switched to study {study_code} for user {request.user.pk}")
        return True
        
    except Study.DoesNotExist:
        logger.error(f"Study {study_code} not found for user {request.user.pk}")
        return False
    except Exception as e:
        logger.error(f"Error switching to study {study_code}: {e}")
        return False