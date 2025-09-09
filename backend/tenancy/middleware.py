# backend/tenancy/middleware.py - COMPLETE OPTIMIZED VERSION
"""
Optimized middleware for ResSync platform with comprehensive caching,
connection pooling, and performance improvements.
"""
import logging
import re
from typing import Optional, Set, Dict, Any
from contextlib import contextmanager
from functools import lru_cache
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction, connections
from django.utils.functional import SimpleLazyObject
from django.utils.deprecation import MiddlewareMixin
from .models import StudyMembership, Study, RolePermission, StudySite
from .db_loader import study_db_manager
from .db_router import set_current_db, get_current_db
import time

logger = logging.getLogger(__name__)


class StudyRoutingMiddleware:
    """
    Main middleware for study-based database routing with optimizations:
    - Multi-level caching (request, session, Redis)
    - Connection pooling management
    - Lazy loading of expensive operations
    - Compiled regex patterns for path matching
    """
    
    # Path configurations
    EXCLUDED_PATHS = frozenset([
        "/select-study/", "/accounts/", "/admin/", "/secret-admin/",
        "/rosetta/", "/i18n/", "/static/", "/media/", "/favicon.ico",
        "/robots.txt", "/sitemap.xml", "/health/", "/metrics/"
    ])
    
    PROTECTED_PATHS = frozenset([
        "/secret-admin/", "/rosetta/"
    ])
    
    API_PATHS = frozenset([
        "/api/", "/graphql/"
    ])
    
    # Cache configurations
    CACHE_PREFIX = "study_mw_"
    CACHE_TTL = 300  # 5 minutes
    SHORT_CACHE_TTL = 60  # 1 minute for frequently changing data
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._compiled_patterns = self._compile_patterns()
        self._path_cache = {}  # Cache path check results
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Pre-compile regex patterns for performance"""
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
            'static': re.compile(r'^/(static|media)/'),
        }
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Main middleware processing"""
        # Performance tracking
        middleware_start = self._get_timestamp()
        
        try:
            # Fast path for static files
            if self._is_static_request(request):
                return self.get_response(request)
            
            # Security check for protected paths
            if self._check_protected_path(request):
                raise Http404("Page not found")
            
            # Check if path should use default database
            if self._should_use_default_db(request):
                set_current_db("default")
                return self.get_response(request)
            
            # Handle unauthenticated users
            if not request.user.is_authenticated:
                set_current_db("default")
                return self.get_response(request)
            
            # Superusers always use default database
            if request.user.is_superuser:
                set_current_db("default")
                setattr(request, "is_superuser_mode", True)
                return self.get_response(request)
            
            # Get and validate study
            study = self._get_validated_study(request)
            if not study:
                return self._handle_no_study(request)
            
            # Setup study context with lazy loading
            self._setup_study_context(request, study)
            
            # Process request with study database
            response = self._process_with_study_db(request, study)
            
            # Add performance headers in debug mode
            if settings.DEBUG:
                elapsed = self._get_timestamp() - middleware_start
                response['X-Processing-Time'] = f"{elapsed:.3f}ms"
                response['X-Study-DB'] = study.db_name
            
            return response
            
        except Exception as e:
            logger.error(f"Middleware error for user {getattr(request.user, 'pk', 'anonymous')}: {e}", exc_info=True)
            set_current_db("default")
            
            # Return JSON error for API requests
            if self._is_api_request(request):
                return JsonResponse({
                    'error': 'Internal server error',
                    'detail': str(e) if settings.DEBUG else 'An error occurred',
                    'user': getattr(request.user, 'pk', 'anonymous'),
                    'path': request.path
                }, status=500)
            
            raise
        
        finally:
            # Always reset to default database
            set_current_db("default")
    
    def _get_timestamp(self) -> float:
        """Get current timestamp in milliseconds"""
        return time.time() * 1000
    
    def _is_static_request(self, request: HttpRequest) -> bool:
        """Check if request is for static content"""
        return bool(self._compiled_patterns['static'].match(request.path))
    
    def _is_api_request(self, request: HttpRequest) -> bool:
        """Check if request is for API endpoint"""
        return bool(self._compiled_patterns['api'].match(request.path))
    
    def _check_protected_path(self, request: HttpRequest) -> bool:
        """Check if path is protected for non-superusers"""
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return False
        
        path = request.path
        
        # Check cache first
        cache_key = f"path_protected_{path}"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
        
        # Check pattern
        is_protected = bool(self._compiled_patterns['protected'].match(path))
        
        # Cache result (limit cache size, remove oldest if needed)
        if len(self._path_cache) >= 1000:
            oldest_key = next(iter(self._path_cache))
            self._path_cache.pop(oldest_key)
        self._path_cache[cache_key] = is_protected
        
        return is_protected
    
    def _should_use_default_db(self, request: HttpRequest) -> bool:
        """Check if request should use default database"""
        path = request.path
        
        # Check cache
        cache_key = f"path_excluded_{path}"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
        
        # Check pattern
        use_default = bool(self._compiled_patterns['excluded'].match(path))
        
        # Cache result (limit cache size, remove oldest if needed)
        if len(self._path_cache) >= 1000:
            oldest_key = next(iter(self._path_cache))
            self._path_cache.pop(oldest_key)
        self._path_cache[cache_key] = use_default
        
        return use_default
    
    def _get_validated_study(self, request: HttpRequest) -> Optional[Study]:
        """
        Get and validate study with multi-level caching:
        1. Request-level cache (fastest)
        2. Session cache
        3. Redis cache
        4. Database (slowest)
        """
        study_id = request.session.get("current_study")
        if not study_id:
            return None
        
        # Level 1: Request cache
        if hasattr(request, '_cached_study'):
            return getattr(request, '_cached_study', None)
        
        # Level 2: Session cache with validation
        session_cache_key = f"study_obj_{study_id}"
        if session_cache_key in request.session:
            cached_data = request.session[session_cache_key]
            if self._validate_cached_study(cached_data):
                study = self._create_study_from_cache(cached_data)
                setattr(request, '_cached_study', study)
                return study
        
        # Level 3: Redis cache
        redis_cache_key = f"{self.CACHE_PREFIX}study_{study_id}_user_{request.user.pk}"
        cached_data = cache.get(redis_cache_key)
        
        if cached_data:
            if self._validate_cached_study(cached_data):
                study = self._create_study_from_cache(cached_data)
                setattr(request, '_cached_study', study)
                # Update session cache
                request.session[session_cache_key] = cached_data
                return study
        
        # Level 4: Database query with optimizations
        try:
            with transaction.atomic():
                # Lock bản ghi Study trước, không join gì cả để tránh lỗi FOR UPDATE với outer join
                study = (
                    Study.objects
                    .select_for_update(nowait=True)
                    .get(id=study_id, status=Study.Status.ACTIVE)
                )
                # Sau đó mới truy vấn các quan hệ nếu cần
                study = Study.objects.select_related('created_by').get(pk=study.pk)
                # Access translations if needed, e.g., study.translations.<field>
                
                # Verify user has access
                has_access = (
                    StudyMembership.objects
                    .filter(
                        user=request.user,
                        study=study,
                        is_active=True
                    )
                    .exists()
                )
                
                if not has_access:
                    request.session.pop("current_study", None)
                    request.session.pop(session_cache_key, None)
                    logger.warning(f"User {request.user.pk} has no access to study {study_id}")
                    return None
                
                # Cache the study data
                cache_data = self._create_cache_data(study)
                
                # Update all cache levels
                cache.set(redis_cache_key, cache_data, self.CACHE_TTL)
                request.session[session_cache_key] = cache_data
                setattr(request, '_cached_study', study)
                return study
                
        except Study.DoesNotExist:
            request.session.pop("current_study", None)
            logger.warning(f"Study {study_id} not found or inactive")
            return None
        except Exception as e:
            logger.error(f"Error fetching study {study_id}: {e}")
            return None
    
    def _validate_cached_study(self, cached_data: Dict[str, Any]) -> bool:
        """Validate cached study data"""
        if not cached_data:
            return False
        
        # Check required fields
        required_fields = ['id', 'code', 'db_name', 'status']
        if not all(field in cached_data for field in required_fields):
            return False
        
        # Check if study is still active
        return cached_data.get('status') == Study.Status.ACTIVE
    
    def _create_study_from_cache(self, cached_data: Dict[str, Any]) -> Study:
        """Create Study object from cached data"""
        study = Study(
            id=cached_data['id'],
            code=cached_data['code'],
            db_name=cached_data['db_name'],
            status=cached_data['status']
        )
        
        # Add additional cached fields if available
        for field in ['created_at', 'updated_at']:
            if field in cached_data:
                setattr(study, field, cached_data[field])
        
        return study
    
    def _create_cache_data(self, study: Study) -> Dict[str, Any]:
        """Create cache data from Study object"""
        return {
            'id': getattr(study, 'id', None),
            'code': getattr(study, 'code', None),
            'db_name': getattr(study, 'db_name', None),
            'status': getattr(study, 'status', None),
            'created_at': study.created_at.isoformat() if hasattr(study, 'created_at') and study.created_at else None,
            'updated_at': study.updated_at.isoformat() if hasattr(study, 'updated_at') and study.updated_at else None,
        }
    
    def _setup_study_context(self, request: HttpRequest, study: Study) -> None:
        """
        Setup study context with lazy loading for performance.
        Uses SimpleLazyObject to defer expensive operations until needed.
        """
        setattr(request, 'study', study)
        # Use lazy loading for expensive operations
        setattr(request, 'study_memberships', SimpleLazyObject(
            lambda: self._get_cached_memberships(request.user, study)
        ))
        setattr(request, 'study_permissions', SimpleLazyObject(
            lambda: self._get_cached_permissions(request.user, study)
        ))
        setattr(request, 'site_codes', SimpleLazyObject(
            lambda: self._get_cached_site_codes(request.user, study)
        ))
        # Add study info to request for logging
        setattr(request, 'study_code', getattr(study, 'code', None))
        setattr(request, 'study_id', getattr(study, 'id', None))
    
    def _get_cached_memberships(self, user, study) -> list:
        """Get cached study memberships with optimized query"""
        cache_key = f"{self.CACHE_PREFIX}memberships_{user.pk}_{study.id}"
        memberships = cache.get(cache_key)
        
        if memberships is None:
            memberships = list(
                StudyMembership.objects
                .select_related('study', 'role')
                .prefetch_related(
                    'study_sites__site',
                    'role__role_permissions__permission'
                )
                .filter(user=user, study=study, is_active=True)
            )
            
            # Cache for shorter time as memberships can change
            cache.set(cache_key, memberships, self.SHORT_CACHE_TTL)
            
            logger.debug(f"Loaded {len(memberships)} memberships for user {user.pk} in study {study.code}")
        
        return memberships
    
    def _get_cached_permissions(self, user, study) -> Set[str]:
        """Get cached study permissions"""
        cache_key = f"{self.CACHE_PREFIX}perms_{user.pk}_{study.id}"
        permissions = cache.get(cache_key)
        
        if permissions is None:
            permissions = set()
            memberships = self._get_cached_memberships(user, study)
            
            # Batch fetch all permissions
            role_ids = [m.role_id for m in memberships]
            if role_ids:
                perms = (
                    RolePermission.objects
                    .filter(role_id__in=role_ids)
                    .select_related('permission')
                    .values_list('permission__code', flat=True)
                )
                permissions.update(perms)
            
            cache.set(cache_key, permissions, self.CACHE_TTL)
            
            logger.debug(f"Loaded {len(permissions)} permissions for user {user.pk} in study {study.code}")
        
        return permissions
    
    def _get_cached_site_codes(self, user, study) -> list:
        """Get cached site codes with optimization"""
        cache_key = f"{self.CACHE_PREFIX}sites_{user.pk}_{study.id}"
        site_codes = cache.get(cache_key)
        
        if site_codes is None:
            site_codes = set()
            memberships = self._get_cached_memberships(user, study)
            
            for membership in memberships:
                if membership.can_access_all_sites:
                    # Get all sites for study
                    all_sites = (
                        StudySite.objects
                        .filter(study=study)
                        .select_related('site')
                        .values_list('site__code', flat=True)
                    )
                    site_codes.update(all_sites)
                else:
                    # Get assigned sites
                    assigned_sites = (
                        membership.study_sites
                        .select_related('site')
                        .values_list('site__code', flat=True)
                    )
                    site_codes.update(assigned_sites)
            
            site_codes = list(site_codes)
            cache.set(cache_key, site_codes, self.CACHE_TTL)
            
            logger.debug(f"Loaded {len(site_codes)} sites for user {user.pk} in study {study.code}")
        
        return site_codes
    
    def _process_with_study_db(self, request: HttpRequest, study: Study) -> HttpResponse:
        """Process request with study database context"""
        try:
            # Set current database
            set_current_db(study.db_name)
            
            # Add study database to connection pool
            study_db_manager.add_study_db(study.db_name)
            
            # Log database switch in debug mode
            if settings.DEBUG:
                logger.debug(f"Switched to database {study.db_name} for user {request.user.pk}")
            
            # Process request
            response = self.get_response(request)
            
            # Add study info to response headers in debug mode
            if settings.DEBUG:
                response['X-Study-Code'] = study.code
                response['X-Database'] = study.db_name
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing with study DB {study.db_name}: {e}", exc_info=True)
            # Try to recover by using default database
            set_current_db("default")
            
            if self._is_api_request(request):
                return JsonResponse({
                    'error': 'Database error',
                    'detail': str(e) if settings.DEBUG else 'Database unavailable',
                    'user': getattr(request.user, 'pk', 'anonymous'),
                    'study': getattr(study, 'id', None)
                }, status=503)
            
            raise
    
    def _handle_no_study(self, request: HttpRequest) -> HttpResponse:
        """Handle case when no valid study is selected"""
        # Check if user has any active studies
        cache_key = f"{self.CACHE_PREFIX}has_studies_{request.user.pk}"
        has_studies = cache.get(cache_key)
        
        if has_studies is None:
            has_studies = (
                StudyMembership.objects
                .filter(
                    user=request.user,
                    study__status=Study.Status.ACTIVE,
                    is_active=True
                )
                .exists()
            )
            # Cache for short time
            cache.set(cache_key, has_studies, self.SHORT_CACHE_TTL)
        
        if has_studies:
            logger.info(f"User {request.user.pk} redirected to study selection")
            return redirect("select_study")
        
        # User has no active studies
        messages.error(request, "You have no access to any active studies.")
        logger.warning(f"User {request.user.pk} has no active study access")
        
        return redirect("login")

    def _setup_language(self, request):
        """Setup language with Vietnamese as default"""
        from django.utils.translation import get_language, activate
        
        # Get current language from session or cookies
        language = None
        
        # Check session first
        if hasattr(request, 'session'):
            language = request.session.get('django_language')
        
        # Check cookie if not in session
        if not language and hasattr(request, 'COOKIES'):
            language = request.COOKIES.get('django_language')
        
        # Default to Vietnamese if no language set
        if not language:
            language = 'vi'
            activate(language)
            if hasattr(request, 'session'):
                request.session['django_language'] = language
        else:
            activate(language)
        
        return language

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