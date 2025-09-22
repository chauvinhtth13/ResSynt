# backend/tenancy/middleware.py - COMPLETE OPTIMIZED VERSION
"""
Optimized middleware for ResSync platform with comprehensive caching,
connection pooling, and performance improvements.
"""
import logging
import re
from typing import Optional, Set, Dict, Any
from functools import lru_cache
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.utils.functional import SimpleLazyObject
from django.utils import timezone
from .models import StudyMembership, Study, RolePermission, StudySite
from .db_loader import study_db_manager
from .db_router import set_current_db
import time

logger = logging.getLogger(__name__)

class StudyRoutingMiddleware:
    """
    Main middleware for study-based database routing.
    Optimized for performance with caching and lazy loading.
    """
    
    # Path configurations
    EXCLUDED_PATHS = frozenset([
        "/", "/select-study/", "/accounts/", "/admin/", "/secret-admin/",
        "/rosetta/", "/i18n/", "/static/", "/media/", "/favicon.ico",
        "/robots.txt", "/sitemap.xml", "/health/", "/metrics/", "/logout/"
    ])
    
    PROTECTED_PATHS = frozenset(["/secret-admin/", "/rosetta/"])
    API_PATHS = frozenset(["/api/", "/graphql/"])
    STATIC_PATHS = frozenset(["/static/", "/media/"])
    
    # Cache configurations
    CACHE_PREFIX = "study_"
    CACHE_TTL = 300  # 5 minutes
    SHORT_CACHE_TTL = 60  # 1 minute for frequently changing data
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._compiled_patterns = self._compile_patterns()
    
    @lru_cache(maxsize=128)
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Pre-compile regex patterns for performance (cached)"""
        return {
            'excluded': re.compile(
                r'^(' + '|'.join(re.escape(p) for p in self.EXCLUDED_PATHS) + r')'
            ),
            'protected': re.compile(
                r'^(' + '|'.join(re.escape(p) for p in self.PROTECTED_PATHS) + r')'
            ),
            'api': re.compile(
                r'^(' + '|'.join(re.escape(p) for p in self.API_PATHS) + r')'
            ),
            'static': re.compile(
                r'^(' + '|'.join(re.escape(p) for p in self.STATIC_PATHS) + r')'
            ),
        }
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Main middleware processing with optimized flow"""
        start_time = time.time() if settings.DEBUG else None
        
        try:
            # Fast paths - no database switching needed
            if self._should_skip_processing(request):
                set_current_db("default")
                return self.get_response(request)
            
            # Check authentication
            if not request.user.is_authenticated:
                set_current_db("default")
                return self.get_response(request)
            
            # Superusers use default DB
            if request.user.is_superuser:
                set_current_db("default")
                request.session['is_superuser_mode'] = True
                return self.get_response(request)
            
            # Get study for regular users
            study = self._get_study_for_request(request)
            
            if study:
                # Setup study context
                self._setup_study_context(request, study)
                
                # Switch to study database
                set_current_db(study.db_name)
                study_db_manager.add_study_db(study.db_name)
                
                response = self.get_response(request)
                
                # Add debug headers
                if settings.DEBUG:
                    response['X-Study'] = study.code
                    response['X-Database'] = study.db_name
                    if start_time:
                        response['X-Processing-Time'] = f"{(time.time() - start_time) * 1000:.2f}ms"
                
                return response
            else:
                # No study selected - use default DB
                set_current_db("default")
                return self.get_response(request)
                
        except Exception as e:
            logger.error(f"Middleware error: user={getattr(request.user, 'pk', 'anon')}, path={request.path}, error={e}")
            set_current_db("default")
            
            if self._is_api_request(request):
                return JsonResponse({
                    'error': 'Internal server error',
                    'detail': str(e) if settings.DEBUG else 'An error occurred'
                }, status=500)
            raise
        finally:
            # Always reset to default
            set_current_db("default")
    
    def _should_skip_processing(self, request: HttpRequest) -> bool:
        """Check if request should skip study processing"""
        path = request.path
        
        # Check static files first (most common)
        if self._compiled_patterns['static'].match(path):
            return True
        
        # Check excluded paths
        if self._compiled_patterns['excluded'].match(path):
            return True
        
        # Check protected paths for non-superusers
        if (self._compiled_patterns['protected'].match(path) and 
            hasattr(request, 'user') and 
            request.user.is_authenticated and 
            not request.user.is_superuser):
            raise Http404("Page not found")
        
        return False
    
    def _is_api_request(self, request: HttpRequest) -> bool:
        """Check if request is for API endpoint"""
        return bool(self._compiled_patterns['api'].match(request.path))
    
    def _get_study_for_request(self, request: HttpRequest) -> Optional[Study]:
        """Get study for current request with caching"""
        study_id = request.session.get('current_study')
        if not study_id:
            return None
        
        # Try request-level cache first
        if hasattr(request, '_cached_study'):
            return getattr(request, '_cached_study')
        
        # Try Redis cache
        cache_key = f"{self.CACHE_PREFIX}study_{study_id}_user_{request.user.pk}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            study = self._create_study_from_cache(cached_data)
            setattr(request, '_cached_study', study)
            return study
        
        # Load from database
        try:
            study = (
                Study.objects
                .select_related('created_by')
                .get(
                    id=study_id,
                    status=Study.Status.ACTIVE,
                    memberships__user=request.user,
                    memberships__is_active=True
                )
            )
            
            # Cache the study
            cache_data = {
                'id': study.pk,
                'code': study.code,
                'db_name': study.db_name,
                'status': study.status,
            }
            cache.set(cache_key, cache_data, self.CACHE_TTL)
            
            setattr(request, '_cached_study', study)
            return study
            
        except Study.DoesNotExist:
            # Clear invalid study from session
            request.session.pop('current_study', None)
            logger.warning(f"Invalid study {study_id} for user {request.user.pk}")
            return None
    
    def _create_study_from_cache(self, cache_data: Dict[str, Any]) -> Study:
        """Create Study object from cached data"""
        study = Study(
            id=cache_data['id'],
            code=cache_data['code'],
            db_name=cache_data['db_name'],
            status=cache_data.get('status', Study.Status.ACTIVE)
        )
        return study
    
    def _setup_study_context(self, request: HttpRequest, study: Study) -> None:
        """Setup study context with lazy loading and auto-update access tracking"""
        setattr(request, 'study', study)
        setattr(request, 'study_id', study.pk)
        setattr(request, 'study_code', study.code)
        
        # AUTO-UPDATE: Track user's study access
        self._update_study_access(request.user, study)
        
        # Use lazy loading for expensive operations
        setattr(request, 'study_permissions', SimpleLazyObject(
            lambda: self._get_permissions(request.user, study)
        ))
        setattr(request, 'site_codes', SimpleLazyObject(
            lambda: self._get_site_codes(request.user, study)
        ))
    
    def _update_study_access(self, user, study) -> None:
        """Auto-update user's last study access"""
        try:
            # Import locally để tránh circular import
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Only update if study changed or last access was > 5 minutes ago
            should_update = False
            
            # Check if attributes exist first
            if hasattr(user, 'last_study_accessed_id'):
                if user.last_study_accessed_id != study.id:
                    should_update = True
                elif hasattr(user, 'last_study_accessed_at') and user.last_study_accessed_at:
                    time_diff = timezone.now() - user.last_study_accessed_at
                    if time_diff.total_seconds() > 300:  # 5 minutes
                        should_update = True
                else:
                    should_update = True
            else:
                should_update = True
            
            if should_update:
                # Update using update() for better performance
                User.objects.filter(pk=user.pk).update(
                    last_study_accessed=study,
                    last_study_accessed_at=timezone.now()
                )
                
                # Refresh user object to get updated values
                user.refresh_from_db(fields=['last_study_accessed', 'last_study_accessed_at'])
                
                # Log the access
                logger.debug(f"Updated study access: user={user.username}, study={study.code}")
                
        except Exception as e:
            # Don't break request if tracking fails
            logger.error(f"Failed to update study access tracking: {e}")

    def _get_permissions(self, user, study) -> Set[str]:
        """Get cached permissions for user in study"""
        cache_key = f"{self.CACHE_PREFIX}perms_{user.pk}_{study.id}"
        permissions = cache.get(cache_key)
        
        if permissions is None:
            permissions = set()
            memberships = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            ).select_related('role')
            
            for membership in memberships:
                perms = (
                    RolePermission.objects
                    .filter(role=membership.role)
                    .select_related('permission')
                    .values_list('permission__code', flat=True)
                )
                permissions.update(perms)
            
            cache.set(cache_key, permissions, self.CACHE_TTL)
        
        return permissions
    
    def _get_site_codes(self, user, study) -> list:
        """Get cached site codes for user in study"""
        cache_key = f"{self.CACHE_PREFIX}sites_{user.pk}_{study.id}"
        site_codes = cache.get(cache_key)
        
        if site_codes is None:
            site_codes = set()
            memberships = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            )
            
            for membership in memberships:
                if membership.can_access_all_sites:
                    all_sites = (
                        StudySite.objects
                        .filter(study=study)
                        .select_related('site')
                        .values_list('site__code', flat=True)
                    )
                    site_codes.update(all_sites)
                else:
                    assigned_sites = (
                        membership.study_sites
                        .select_related('site')
                        .values_list('site__code', flat=True)
                    )
                    site_codes.update(assigned_sites)
            
            site_codes = list(site_codes)
            cache.set(cache_key, site_codes, self.CACHE_TTL)
        
        return site_codes

class CacheControlMiddleware:
    """
    Optimized cache control middleware for static and dynamic content.
    Implements intelligent caching strategies based on content type.
    """
    
    # Static content paths that can be cached
    CACHEABLE_PATHS = frozenset(['/static/', '/media/', '/assets/'])
    
    # File extensions that can be cached long-term
    CACHEABLE_EXTENSIONS = frozenset([
        '.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg',
        '.woff', '.woff2', '.ttf', '.eot', '.ico', '.webp'
    ])
    
    # Security headers for authenticated users
    NO_CACHE_HEADERS = {
        "Cache-Control": "no-cache, no-store, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    
    # Cache headers for static content
    STATIC_CACHE_HEADERS = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "Vary": "Accept-Encoding",
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # Determine caching strategy
        if self._is_static_content(request):
            # Long-term caching for static content
            self._apply_static_cache_headers(response)
        elif request.user.is_authenticated:
            # No caching for authenticated users
            self._apply_no_cache_headers(response)
        else:
            # Short-term caching for anonymous users
            self._apply_anonymous_cache_headers(response)
        
        return response
    
    def _is_static_content(self, request: HttpRequest) -> bool:
        """Check if request is for static content"""
        path = request.path
        
        # Check if path is in cacheable paths
        if any(path.startswith(p) for p in self.CACHEABLE_PATHS):
            return True
        
        # Check file extension
        for ext in self.CACHEABLE_EXTENSIONS:
            if path.endswith(ext):
                return True
        
        return False
    
    def _apply_static_cache_headers(self, response: HttpResponse) -> None:
        """Apply cache headers for static content"""
        for header, value in self.STATIC_CACHE_HEADERS.items():
            response[header] = value
    
    def _apply_no_cache_headers(self, response: HttpResponse) -> None:
        """Apply no-cache headers for authenticated users"""
        for header, value in self.NO_CACHE_HEADERS.items():
            response[header] = value
    
    def _apply_anonymous_cache_headers(self, response: HttpResponse) -> None:
        """Apply cache headers for anonymous users"""
        # Cache for 5 minutes for anonymous users
        response["Cache-Control"] = "public, max-age=300"
        response["Vary"] = "Cookie, Accept-Encoding"

class SecurityHeadersMiddleware:
    """
    Comprehensive security headers middleware.
    Adds security headers to all responses for protection against common attacks.
    """
    
    # Base security headers applied to all responses
    BASE_SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    
    # Content Security Policy for different contexts
    CSP_POLICIES = {
        'default': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        ),
        'admin': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self' data:; "
            "frame-src 'self';"
        ),
        'api': (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # Apply base security headers
        for header, value in self.BASE_SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value
        
        # Apply CSP based on path
        csp_policy = self._get_csp_policy(request)
        if csp_policy and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = csp_policy
        
        # Add HSTS for HTTPS connections
        if request.is_secure():
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        return response
    
    def _get_csp_policy(self, request: HttpRequest) -> str:
        """Get appropriate CSP policy based on request path"""
        path = request.path
        
        if path.startswith('/admin/'):
            return self.CSP_POLICIES['admin']
        elif path.startswith('/api/'):
            return self.CSP_POLICIES['api']
        else:
            return self.CSP_POLICIES['default']

class PerformanceMonitoringMiddleware:
    """
    Performance monitoring middleware for tracking request metrics.
    Useful for identifying bottlenecks and optimization opportunities.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip monitoring for static files
        if request.path.startswith(('/static/', '/media/')):
            return self.get_response(request)
        
        # Start timing
        start_time = time.time()
        queries_before = 0
        connection = None
        if settings.DEBUG:
            from django.db import connection as db_connection
            connection = db_connection
            queries_before = len(connection.queries)
        
        # Process request
        response = self.get_response(request)
        
        # Calculate metrics
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Add performance headers
        response['X-Response-Time'] = f"{duration:.2f}ms"
        
        if settings.DEBUG and connection is not None:
            queries_after = len(connection.queries)
            query_count = queries_after - queries_before
            response['X-DB-Query-Count'] = str(query_count)
            
            # Log slow requests
            if duration > 1000:  # Log requests taking more than 1 second
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}ms with {query_count} queries"
                )
        
        # Log to metrics system if available
        self._log_metrics(request, response, duration)
        
        return response
    
    def _log_metrics(self, request: HttpRequest, response: HttpResponse, duration: float) -> None:
        """Log metrics to monitoring system"""
        # This could be integrated with systems like Prometheus, DataDog, etc.
        if settings.DEBUG:
            logger.debug(
                f"Request metrics: method={request.method} "
                f"path={request.path} status={response.status_code} "
                f"duration={duration:.2f}ms user={getattr(request.user, 'pk', 'anonymous')}"
            )

class DatabaseConnectionCleanupMiddleware:
    """
    Middleware to ensure database connections are properly cleaned up.
    Prevents connection leaks and manages connection pool.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            response = self.get_response(request)
        finally:
            # Clean up any study database connections
            self._cleanup_connections(request)
        
        return response
    
    def _cleanup_connections(self, request: HttpRequest) -> None:
        """Clean up database connections after request"""
        # Get study database if it was used
        study = getattr(request, 'study', None)
        
        if study and study.db_name in connections:
            try:
                # Close connection if it's not being pooled
                conn = connections[study.db_name]
                if isinstance(conn.queries_logged, int) and conn.queries_logged > 100:
                    conn.close()
                    logger.debug(f"Closed connection to {study.db_name} due to high query count")
            except Exception as e:
                logger.error(f"Error cleaning up connection to {study.db_name}: {e}")
        
        # Clean up any unusable connections
        for alias in connections:
            try:
                connections[alias].close_if_unusable_or_obsolete()
            except Exception as e:
                logger.error(f"Error checking connection {alias}: {e}")
