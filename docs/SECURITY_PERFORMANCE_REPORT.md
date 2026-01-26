# Security & Performance Analysis Report

**Project:** ResSynt - Research Data Management Platform  
**Date:** January 26, 2026  
**Analyzer:** GitHub Copilot (Claude Opus 4.5)

---

## Executive Summary

The codebase demonstrates **solid security foundations** with well-implemented protections. However, there are several areas where improvements can enhance performance and address potential security gaps.

| Category | Status | Critical Issues | Recommendations |
|----------|--------|-----------------|-----------------|
| Security | ✅ Good | 0 | 8 |
| Performance | ⚠️ Moderate | 2 | 10 |
| Code Quality | ✅ Good | 0 | 5 |

---

## 🔒 Security Analysis

### ✅ Security Strengths (Well Implemented)

1. **Password Security**
   - Argon2 as primary password hasher (state-of-the-art)
   - Password validators: min length 8, similarity check, common password check
   - `must_change_password` flag for first-time logins

2. **Authentication Protection**
   - Django-axes for brute force protection (7 failures = lockout)
   - Allauth rate limits (5 failed logins/min)
   - Session idle timeout (1 hour by default)
   - `SESSION_SAVE_EVERY_REQUEST = True` for activity tracking

3. **CSRF/XSS Protection**
   - CSRF tokens stored in sessions (`CSRF_USE_SESSIONS = True`)
   - CSRF cookie with `Strict` SameSite
   - Content Security Policy (CSP) with nonces
   - X-Frame-Options: DENY

4. **Input Sanitization**
   - Comprehensive `SecuritySanitizer` with pre-compiled regex patterns
   - XSS, SQL injection, and command injection detection
   - HTML escaping and CSV injection prevention
   - Unicode normalization (NFKC)

5. **Audit Trail Integrity**
   - HMAC-SHA256 checksums for tamper detection
   - Constant-time comparison to prevent timing attacks
   - Separate `AUDIT_INTEGRITY_SECRET` option

6. **HTTPS Hardening (Production)**
   - HSTS with 1-year max-age
   - SSL redirect enabled
   - Secure cookies

---

### ⚠️ Security Recommendations

#### 1. **Rate Limiter - Race Condition** (Medium Risk)

**File:** [backends/audit_logs/utils/rate_limiter.py](backends/audit_logs/utils/rate_limiter.py#L40-L54)

**Issue:** Non-atomic read-then-write pattern in rate limiting can be bypassed with concurrent requests.

```python
# Current code (race condition)
count = cache.get(cache_key, 0)
if count >= max_requests:
    # ...
cache.set(cache_key, count + 1, window)
```

**Solution:**
```python
# Use atomic increment with Redis
from django.core.cache import cache

def rate_limit(key_prefix: str, max_requests: int = 10, window: int = 60):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = f'rate_limit:{key_prefix}:{ip}:{user_id}'
            
            try:
                # Atomic increment - works with Redis
                count = cache.incr(cache_key)
            except ValueError:
                # Key doesn't exist, create it
                cache.set(cache_key, 1, window)
                count = 1
            
            if count > max_requests:
                # Rate limit exceeded
                return HttpResponse('Rate limit exceeded', status=429)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

#### 2. **IP Address Extraction Security** (Medium Risk)

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py#L180-L195)

**Issue:** X-Forwarded-For header can be spoofed. The current implementation trusts the header without proper validation.

**Current code:**
```python
xff = request.META.get('HTTP_X_FORWARDED_FOR')
if xff:
    ips = [ip.strip() for ip in xff.split(',')]
    proxy_count = getattr(settings, 'AXES_IPWARE_PROXY_COUNT', 1)
    client_index = max(0, len(ips) - proxy_count - 1)
    return ips[client_index][:45]
```

**Solution:**
```python
import ipaddress

def _get_client_ip(self, request: HttpRequest) -> str:
    """
    Get client IP with proxy awareness and validation.
    """
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if xff:
        ips = [ip.strip() for ip in xff.split(',')]
        proxy_count = getattr(settings, 'AXES_IPWARE_PROXY_COUNT', 1)
        
        # Get the IP that should be the client
        if len(ips) > proxy_count:
            client_ip = ips[-(proxy_count + 1)]
        else:
            client_ip = ips[0]
        
        # Validate IP format
        try:
            ipaddress.ip_address(client_ip.strip())
            return client_ip.strip()[:45]
        except ValueError:
            pass
    
    return request.META.get('REMOTE_ADDR', '127.0.0.1')[:45]
```

---

#### 3. **Study Code Injection Prevention** (Low Risk)

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py#L135-L150)

**Current:** Validates study code with regex `^[A-Z0-9_]{2,20}$`

**Enhancement:** Add additional validation in database queries:
```python
def _get_study_by_code(self, request: HttpRequest, code: str) -> Optional[Study]:
    # Already validated by regex, but add parameterized query safety
    cache_key = f"{self.CACHE_PREFIX}study_{code}_{request.user.pk}"
    study = cache.get(cache_key)
    
    if study is not None:
        return study
    
    try:
        # Django ORM already uses parameterized queries - SAFE
        study = Study.objects.select_related('created_by').get(
            code__iexact=code,  # Case-insensitive but exact match
            memberships__user=request.user,
            memberships__is_active=True,
        )
```

---

#### 4. **Session Fixation Enhancement** (Low Risk)

**File:** [config/settings/base.py](config/settings/base.py)

**Add:** Regenerate session ID after login:
```python
# In allauth adapter or signal
from django.contrib.auth.signals import user_logged_in

def regenerate_session(sender, request, user, **kwargs):
    request.session.cycle_key()

user_logged_in.connect(regenerate_session)
```

---

#### 5. **Sensitive Data in Logs** (Low Risk)

**File:** [backends/audit_logs/utils/rate_limiter.py](backends/audit_logs/utils/rate_limiter.py#L45-L50)

**Issue:** User-agent is logged which could contain sensitive info.

**Solution:** Truncate and sanitize:
```python
user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:100]
# Remove potential PII from user-agent
user_agent = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+', '[EMAIL]', user_agent)
```

---

#### 6. **Cache Key Collision Prevention** (Low Risk)

**File:** [backends/tenancy/utils/tenancy_utils.py](backends/tenancy/utils/tenancy_utils.py#L34-L40)

**Enhancement:**
```python
@classmethod
def _cache_key(cls, *parts) -> str:
    """Generate collision-resistant cache key."""
    key = ':'.join(str(p) for p in parts)  # Use : separator instead of _
    if len(key) > 200:
        key = hashlib.sha256(key.encode()).hexdigest()
    return f"{cls.CACHE_PREFIX}:{key}"
```

---

#### 7. **Add Security Headers** (Enhancement)

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py#L45-L52)

**Add:**
```python
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    'X-XSS-Protection': '1; mode=block',  # Add this
    'Cross-Origin-Embedder-Policy': 'require-corp',  # Add this
    'Cross-Origin-Opener-Policy': 'same-origin',  # Already in Django settings
}
```

---

#### 8. **Database Connection String Security** (Enhancement)

**File:** [config/settings/prod.py](config/settings/prod.py)

**Ensure:** Database passwords are not logged:
```python
LOGGING = {
    'filters': {
        'hide_sensitive': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: 'password' not in str(record.msg).lower(),
        },
    },
}
```

---

## ⚡ Performance Analysis

### ✅ Performance Strengths

1. **Pre-compiled Regex Patterns**
   - Sanitizer patterns compiled at module load
   - Middleware patterns compiled as class attributes

2. **Two-Layer Caching**
   - Django cache (Redis/LocMem) + Instance cache
   - 5-minute TTL for permissions
   - Cache key hashing for long keys

3. **Database Optimization**
   - `select_related()` for foreign keys
   - `prefetch_related()` for M2M relations
   - Connection pooling with `CONN_MAX_AGE=60`

4. **Lazy Loading**
   - `SimpleLazyObject` for study permissions
   - Request-level caching (`request._study_cache`)

---

### 🔴 Critical Performance Issues

#### Issue 1: N+1 Query in Dashboard View

**File:** [backends/api/base/views.py](backends/api/base/views.py#L95-L110)

**Problem:** The `dashboard` view makes a separate query for membership after study is already loaded.

```python
# Current - causes extra query
user_membership = StudyMembership.objects.filter(
    user=request.user,
    study=study,
    is_active=True
).select_related('group').first()
```

**Solution:**
```python
# Include membership in middleware's study loading
def _setup_study_context(self, request: HttpRequest, study: Study) -> None:
    request.study = study
    # Load membership at the same time
    from backends.tenancy.models import StudyMembership
    request.study_membership = StudyMembership.objects.filter(
        user=request.user,
        study=study,
        is_active=True
    ).select_related('group').first()
```

---

#### Issue 2: Repeated Study Queries

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py#L260-L290)

**Problem:** Study is queried from session and URL separately, potentially causing duplicate queries.

**Solution:** Consolidate into single cached query:
```python
def _get_study_for_request(self, request: HttpRequest, path: str) -> Optional[Study]:
    """Get study with request-level caching."""
    # Check request-level cache first
    if hasattr(request, '_resolved_study'):
        return request._resolved_study
    
    code = self._extract_study_code(path)
    study = None
    
    if code:
        study = self._get_study_by_code(request, code)
    
    if not study:
        study = self._get_study_from_session(request)
    
    request._resolved_study = study
    return study
```

---

### ⚠️ Performance Recommendations

#### 1. **Optimize Permission Loading** (High Impact)

**File:** [backends/tenancy/utils/tenancy_utils.py](backends/tenancy/utils/tenancy_utils.py#L45-L85)

**Issue:** Permissions are loaded per-request even with caching.

**Solution - Use Database-Level Caching:**
```python
@classmethod
def get_user_permissions(cls, user, study) -> Set[str]:
    """Get user permissions with optimized query."""
    if not user or not study:
        return set()
    
    cache_key = cls._cache_key('perms', user.pk, study.pk)
    permissions = cache.get(cache_key)
    
    if permissions is not None:
        return permissions
    
    try:
        # Single optimized query with values_list
        app_label = f'study_{study.code.lower()}'
        
        permissions = set(
            Permission.objects.filter(
                group__studymembership__user=user,
                group__studymembership__study=study,
                group__studymembership__is_active=True,
                content_type__app_label=app_label
            ).values_list('codename', flat=True).distinct()
        )
        
        cache.set(cache_key, permissions, cls.CACHE_TTL)
        
    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        permissions = set()
    
    return permissions
```

---

#### 2. **Add Database Query Indexes** (High Impact)

**File:** [backends/tenancy/models/user.py](backends/tenancy/models/user.py#L75-L80)

**Add composite indexes for common queries:**
```python
class Meta:
    db_table = 'auth_user'
    indexes = [
        models.Index(fields=['username']),
        models.Index(fields=['email']),
        models.Index(fields=['is_active']),
        # Add these composite indexes
        models.Index(fields=['is_active', 'is_superuser']),
        models.Index(fields=['last_login'], name='user_last_login_idx'),
    ]
```

**For StudyMembership model:**
```python
class Meta:
    indexes = [
        models.Index(fields=['user', 'study', 'is_active']),
        models.Index(fields=['study', 'is_active']),
    ]
    constraints = [
        models.UniqueConstraint(
            fields=['user', 'study'],
            name='unique_user_study_membership'
        ),
    ]
```

---

#### 3. **Cache Study List Queries** (Medium Impact)

**File:** [backends/api/base/services/study_service.py](backends/api/base/services/study_service.py#L20-L65)

**Enhancement:**
```python
@staticmethod
def get_user_studies(user, search_query: str = '') -> List[Study]:
    """Get studies with improved caching."""
    # Use shorter cache key
    cache_key = f'usr_studies:{user.pk}:{hash(search_query) if search_query else ""}'
    
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    studies = list(
        Study.objects
        .filter(
            memberships__user=user,
            memberships__is_active=True,
            status__in=[Study.Status.ACTIVE, Study.Status.ARCHIVED]
        )
        .only('id', 'code', 'name', 'status', 'db_name')  # Only needed fields
        .distinct()
        .order_by('code')
    )
    
    if search_query:
        search_lower = search_query.lower()
        studies = [s for s in studies if search_lower in s.code.lower() or search_lower in s.name.lower()]
    
    cache.set(cache_key, studies, 300)
    return studies
```

---

#### 4. **Reduce Middleware Processing** (Medium Impact)

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py)

**Issue:** Every request goes through full middleware processing.

**Solution - Early exit for static paths:**
```python
def __call__(self, request: HttpRequest) -> HttpResponse:
    path = request.path
    
    # Ultra-fast path for static files (no timing, no axes)
    if path.startswith(('/static/', '/media/', '/favicon.ico')):
        response = self.get_response(request)
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
    
    # Continue with full processing for other paths
    request._start_time = time.time()
    # ...
```

---

#### 5. **Optimize Database Router Caching** (Medium Impact)

**File:** [backends/tenancy/db_router.py](backends/tenancy/db_router.py#L60-L100)

**Enhancement - Use LRU cache:**
```python
from functools import lru_cache

class TenantRouter:
    @lru_cache(maxsize=128)
    def _get_cached_db_for_app(self, app_label: str) -> str:
        """Cached database lookup for app label."""
        if app_label in self.MANAGEMENT_APPS:
            return 'default'
        if app_label in self.STUDY_APPS or app_label.startswith('study_'):
            return '_STUDY_'
        return '_STUDY_'
    
    def _get_db_for_model(self, model) -> str:
        app_label = model._meta.app_label
        db = self._get_cached_db_for_app(app_label)
        return get_current_db() if db == '_STUDY_' else db
```

---

#### 6. **Connection Pool Tuning** (Medium Impact)

**File:** [config/settings/prod.py](config/settings/prod.py#L51-L60)

**Recommendation:**
```python
DATABASES["default"].update({
    "CONN_HEALTH_CHECKS": True,
    "CONN_MAX_AGE": 600,  # Increase to 10 minutes
    "OPTIONS": {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
})
```

---

#### 7. **Template Caching Improvement** (Low Impact)

**File:** [config/settings/prod.py](config/settings/prod.py#L100-L115)

Already implemented correctly with cached loader. ✅

---

#### 8. **Redis Connection Pooling** (Medium Impact)

**File:** [config/settings/prod.py](config/settings/prod.py#L70-L95)

**Enhancement:**
```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": _redis_url,
        "KEY_PREFIX": "cache",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 100,  # Increase for production
                "timeout": 20,
                "retry_on_timeout": True,
            },
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",  # Faster than pickle
        },
    },
}
```

---

#### 9. **Async Security Alerts** (Low Impact)

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py#L460-L480)

Already using Celery for async alerts. ✅

---

#### 10. **Query Monitoring in Debug Mode** (Enhancement)

Already implemented with `X-DB-Queries` header and `MAX_QUERIES` threshold (100). ✅

---

## 📊 Code Quality Issues

### 1. **Unused Import in __init__.py**

**File:** [backends/api/base/services/__init__.py](backends/api/base/services/__init__.py)

```python
# Remove unused LoginService from __all__
__all__ = [
    'StudyService',  # Only export what exists
]
```

---

### 2. **Exception Handling Specificity**

**File:** [backends/tenancy/db_loader.py](backends/tenancy/db_loader.py)

**Issue:** Broad exception handling hides specific errors.

**Solution:**
```python
except psycopg.OperationalError as e:
    logger.error(f"Database connection error for {db_name}: {e}")
    raise
except psycopg.ProgrammingError as e:
    logger.error(f"SQL error for {db_name}: {e}")
    raise
except Exception as e:
    logger.exception(f"Unexpected error for {db_name}")
    raise
```

---

### 3. **Magic Numbers**

**File:** [backends/tenancy/middleware.py](backends/tenancy/middleware.py)

**Issue:** Magic numbers for timeouts and limits.

**Solution:**
```python
# Add to class constants
SLOW_REQUEST_MS = getattr(settings, 'SLOW_REQUEST_THRESHOLD_MS', 1000)
MAX_QUERIES = getattr(settings, 'MAX_QUERIES_PER_REQUEST', 100)
CACHE_TTL = getattr(settings, 'MIDDLEWARE_CACHE_TTL', 300)
```

---

### 4. **Consistent Error Messages**

**Files:** Various

**Issue:** Mix of English and Vietnamese error messages.

**Recommendation:** Use Django's translation system consistently:
```python
from django.utils.translation import gettext_lazy as _

# Instead of hardcoded strings
error_msg = _('Quá nhiều yêu cầu. Vui lòng thử lại sau.')
```

---

### 5. **Type Hints Completion**

**Files:** Various

**Enhancement:** Add return type hints where missing:
```python
def get_user_studies(user, search_query: str = '') -> List[Study]:
    """..."""
    
def _get_client_ip(self, request: HttpRequest) -> str:
    """..."""
```

---

## 🎯 Priority Action Items

### Immediate (This Sprint)
1. ✅ Fix rate limiter race condition
2. ✅ Add composite database indexes
3. ✅ Optimize permission loading query

### Short-term (Next 2 Sprints)
4. ⬜ Consolidate study queries in middleware
5. ⬜ Implement Redis atomic increment for rate limiting
6. ⬜ Add missing security headers

### Long-term (Backlog)
7. ⬜ IP address validation enhancement
8. ⬜ Connection pool tuning
9. ⬜ Complete type hints
10. ⬜ Internationalize all error messages

---

## 📈 Metrics to Monitor

| Metric | Current | Target | Tool |
|--------|---------|--------|------|
| Avg Response Time | Unknown | < 200ms | New Relic/Datadog |
| DB Queries/Request | Max 100 | < 20 | X-DB-Queries header |
| Cache Hit Rate | Unknown | > 90% | Redis INFO |
| Error Rate (5xx) | Unknown | < 0.1% | Sentry |
| Rate Limit Hits | Unknown | < 1% | Logs |

---

## Conclusion

The ResSynt codebase demonstrates **mature security practices** with comprehensive protection against common vulnerabilities. The main areas for improvement are:

1. **Performance optimizations** around database queries and caching
2. **Race condition fixes** in rate limiting
3. **Minor security enhancements** for defense-in-depth

The architecture is well-designed for multi-tenant study management with proper separation of concerns and caching strategies.

---

*Report generated by GitHub Copilot - Claude Opus 4.5*
