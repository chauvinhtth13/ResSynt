# 🔍 BÁO CÁO KIỂM TRA MÃ NGUỒN - HIỆU SUẤT & BẢO MẬT

**Dự án:** ResSynt Research Management Platform  
**Ngày kiểm tra:** 14/01/2026  
**Phiên bản:** 1.0.0  
**Người kiểm tra:** GitHub Copilot AI Auditor

---

## 📋 MỤC LỤC

1. [Tổng Quan](#tổng-quan)
2. [Vấn Đề Bảo Mật](#vấn-đề-bảo-mật)
   - [Mức Độ Nghiêm Trọng Cao](#-mức-độ-nghiêm-trọng-cao)
   - [Mức Độ Nghiêm Trọng Trung Bình](#-mức-độ-nghiêm-trọng-trung-bình)
   - [Mức Độ Nghiêm Trọng Thấp](#-mức-độ-nghiêm-trọng-thấp)
3. [Vấn Đề Hiệu Suất (Bottleneck)](#vấn-đề-hiệu-suất-bottleneck)
4. [Điểm Tích Cực](#điểm-tích-cực)
5. [Hướng Dẫn Khắc Phục Chi Tiết](#hướng-dẫn-khắc-phục-chi-tiết)
6. [Checklist Triển Khai](#checklist-triển-khai)

---

## TỔNG QUAN

### Đánh Giá Chung

| Tiêu chí | Điểm | Đánh giá |
|----------|------|----------|
| **Bảo mật tổng thể** | 8/10 | ✅ Tốt |
| **Hiệu suất** | 7/10 | ⚠️ Khá |
| **Code Quality** | 8/10 | ✅ Tốt |
| **Best Practices** | 8.5/10 | ✅ Rất tốt |

### Thống Kê Vấn Đề

- 🔴 **Nghiêm trọng cao:** 3 vấn đề
- 🟡 **Nghiêm trọng trung bình:** 5 vấn đề
- 🟢 **Nghiêm trọng thấp:** 6 vấn đề
- ⚡ **Bottleneck hiệu suất:** 7 điểm cần cải thiện

---

## VẤN ĐỀ BẢO MẬT

### 🔴 MỨC ĐỘ NGHIÊM TRỌNG CAO

#### SEC-001: Missing CSP Nonce cho External Scripts

**📍 Vị trí:** `frontends/templates/base.html` (dòng 26)

**❌ Mã hiện tại:**
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
```

**❓ Vấn đề:** Script từ CDN không có nonce attribute trong khi các script khác có. Điều này có thể bị block bởi CSP hoặc tạo lỗ hổng XSS.

**✅ Giải pháp:**
```html
<script nonce="{{ request.csp_nonce }}" src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
```

**📝 Giải thích:** CSP (Content Security Policy) yêu cầu tất cả scripts phải có nonce hợp lệ để chạy. Thiếu nonce có thể:
1. Ngăn script chạy nếu CSP strict
2. Hoặc bypass CSP nếu cho phép, tạo risk XSS

---

#### SEC-002: Potential Information Disclosure trong Error Handling

**📍 Vị trí:** `backends/tenancy/middleware.py` (dòng 239-240)

**❌ Mã hiện tại:**
```python
except Study.DoesNotExist:
    logger.debug(f"Study {code} not accessible by user {request.user.pk}")
    return None
except Exception as e:
    logger.error(f"Error loading study {code}: {type(e).__name__}")
    return None
```

**❓ Vấn đề:** Log chứa study code và user ID có thể bị lộ nếu logs không được bảo vệ đúng cách.

**✅ Giải pháp:**
```python
except Study.DoesNotExist:
    logger.debug(f"Study access denied for user_id={request.user.pk}")
    return None
except Exception as e:
    # Không log study code - tránh information disclosure
    logger.error(f"Study loading error: {type(e).__name__}", extra={
        'user_id': request.user.pk,
        'study_code_hash': hashlib.sha256(code.encode()).hexdigest()[:8]
    })
    return None
```

---

#### SEC-003: Race Condition trong Rate Limiting

**📍 Vị trí:** `backends/tenancy/middleware.py` (dòng 358-365)

**❌ Mã hiện tại:**
```python
# Get current count
count = cache.get(key, 0)

if count >= max_requests:
    # ... rate limit exceeded
    
# Increment counter
cache.set(key, count + 1, window)
```

**❓ Vấn đề:** Race condition - 2 requests đồng thời có thể đọc cùng count và bypass limit.

**✅ Giải pháp:**
```python
from django.core.cache import cache

def _check_rate_limit(self, request: HttpRequest) -> Optional[HttpResponse]:
    """Thread-safe rate limiting using atomic increment."""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    
    if request.user.is_authenticated and request.user.is_superuser:
        return None
        
    ip = self._get_rate_limit_ip(request)
    
    if request.user.is_authenticated:
        key = f"{self.CACHE_PREFIX}rate:{request.user.id}"
        max_requests = 60
    else:
        key = f"{self.CACHE_PREFIX}rate:anon:{ip}"
        max_requests = 10
    
    window = 60
    
    try:
        # Atomic increment - thread-safe
        # incr() tạo key với giá trị 1 nếu chưa tồn tại
        count = cache.incr(key)
    except ValueError:
        # Key không tồn tại, tạo mới với TTL
        cache.set(key, 1, window)
        count = 1
    
    if count > max_requests:
        logger.warning(f"Rate limit exceeded: {key}")
        return HttpResponse('Quá nhiều yêu cầu.', status=429, headers={
            'Retry-After': str(window),
            'X-RateLimit-Limit': str(max_requests),
            'X-RateLimit-Remaining': '0',
        })
    
    return None
```

---

### 🟡 MỨC ĐỘ NGHIÊM TRỌNG TRUNG BÌNH

#### SEC-004: Password Minimum Length Không Đủ Mạnh

**📍 Vị trí:** `config/settings/security.py` (dòng 95)

**❌ Mã hiện tại:**
```python
{
    "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    "OPTIONS": {"min_length": 8},  # Increased from 8 to 10
},
```

**❓ Vấn đề:** Comment nói tăng lên 10 nhưng giá trị vẫn là 8. 8 ký tự không đủ mạnh theo NIST guidelines.

**✅ Giải pháp:**
```python
{
    "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    "OPTIONS": {"min_length": 12},  # NIST recommends 12+ characters
},
# Thêm validator kiểm tra complexity
{
    "NAME": "backends.tenancy.validators.PasswordComplexityValidator",
},
```

**Tạo thêm file:**
```python
# backends/tenancy/validators.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class PasswordComplexityValidator:
    """Ensure password has mixed characters."""
    
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
        if not re.search(r'\d', password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code='password_no_digit',
            )
    
    def get_help_text(self):
        return _("Password must contain uppercase, lowercase, and digits.")
```

---

#### SEC-005: Session Fixation Protection Không Đầy Đủ

**📍 Vị trí:** `backends/tenancy/signals.py` (dòng 32-34)

**❌ Mã hiện tại:**
```python
# Regenerate session to prevent fixation attack
if hasattr(request, 'session'):
    request.session.cycle_key()
```

**❓ Vấn đề:** `cycle_key()` chỉ đổi session key, không xóa session data cũ. Attacker có thể inject session data trước login.

**✅ Giải pháp:**
```python
@receiver(allauth_logged_in)
def handle_allauth_login(request, user, **kwargs):
    """Handle successful login via allauth."""
    try:
        # FULL session fixation protection
        if hasattr(request, 'session'):
            # Lưu language preference (nếu có)
            old_language = request.session.get(settings.LANGUAGE_SESSION_KEY)
            
            # Flush toàn bộ session cũ (xóa data + đổi key)
            request.session.flush()
            
            # Tạo session mới
            request.session.create()
            
            # Khôi phục language
            if old_language:
                request.session[settings.LANGUAGE_SESSION_KEY] = old_language
        
        # ... rest of the code
```

---

#### SEC-006: X-Forwarded-For Trust Issue

**📍 Vị trí:** `backends/tenancy/middleware.py` (dòng 172-182)

**❌ Mã hiện tại:**
```python
def _get_client_ip(self, request: HttpRequest) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        ips = [ip.strip() for ip in xff.split(',')]
        proxy_count = getattr(settings, 'AXES_IPWARE_PROXY_COUNT', 1)
        client_index = max(0, len(ips) - proxy_count - 1)
        return ips[client_index][:45]
```

**❓ Vấn đề:** X-Forwarded-For có thể bị spoof nếu request không qua trusted proxy. Không validate IP format.

**✅ Giải pháp:**
```python
import ipaddress

def _get_client_ip(self, request: HttpRequest) -> str:
    """
    Get client IP with security validation.
    
    CRITICAL: Only trust XFF if behind trusted reverse proxy.
    Configure TRUSTED_PROXY_IPS in settings.
    """
    remote_addr = request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # Chỉ trust XFF nếu request đến từ trusted proxy
    trusted_proxies = getattr(settings, 'TRUSTED_PROXY_IPS', [])
    
    if remote_addr not in trusted_proxies:
        # Direct connection - use REMOTE_ADDR
        return self._validate_ip(remote_addr)
    
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        ips = [ip.strip() for ip in xff.split(',')]
        proxy_count = getattr(settings, 'AXES_IPWARE_PROXY_COUNT', 1)
        
        if len(ips) > proxy_count:
            client_ip = ips[-(proxy_count + 1)]
            return self._validate_ip(client_ip)
    
    return self._validate_ip(remote_addr)

def _validate_ip(self, ip_str: str) -> str:
    """Validate IP address format."""
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip())
        return str(ip_obj)
    except (ValueError, AttributeError):
        return '0.0.0.0'  # Invalid IP
```

**Thêm vào settings:**
```python
# config/settings/prod.py
TRUSTED_PROXY_IPS = env.list('TRUSTED_PROXY_IPS', default=['127.0.0.1'])
```

---

#### SEC-007: Audit Log Checksum Timing Attack

**📍 Vị trí:** `backends/audit_logs/utils/integrity.py` (dòng 141-152)

**❌ Mã hiện tại:**
```python
@staticmethod
def verify_integrity(audit_log) -> bool:
    stored_checksum = audit_log.checksum
    
    if not stored_checksum:
        return False
    
    # Rebuild và compare
    computed = IntegrityChecker.generate_checksum(...)
    return computed == stored_checksum  # Timing attack vulnerable!
```

**❓ Vấn đề:** String comparison `==` có thể bị timing attack - attacker đoán checksum từng byte.

**✅ Giải pháp:**
```python
import hmac

@staticmethod
def verify_integrity(audit_log) -> bool:
    """Verify audit log integrity - timing-safe comparison."""
    stored_checksum = audit_log.checksum
    
    if not stored_checksum:
        logger.warning("⚠️ No checksum stored for audit log %s", audit_log.pk)
        return False
    
    # Rebuild checksum data
    audit_data = {
        'user_id': audit_log.user_id,
        'username': audit_log.username,
        'action': audit_log.action,
        'model_name': audit_log.model_name,
        'patient_id': audit_log.patient_id,
        'timestamp': audit_log.created_at.isoformat() if audit_log.created_at else '',
        'old_data': {},  # Rebuild from details
        'new_data': {},
        'reason': audit_log.reason,
    }
    
    # Get details and rebuild data
    for detail in audit_log.details.all():
        audit_data['old_data'][detail.field_name] = detail.old_value
        audit_data['new_data'][detail.field_name] = detail.new_value
    
    computed_checksum = IntegrityChecker.generate_checksum(audit_data)
    
    # CRITICAL: Timing-safe comparison
    return hmac.compare_digest(computed_checksum, stored_checksum)
```

---

#### SEC-008: Missing BREACH Attack Mitigation

**📍 Vị trí:** `config/settings/prod.py`

**❓ Vấn đề:** Không có protection chống BREACH attack khi dùng HTTPS + compression với secret data.

**✅ Giải pháp:**
```python
# config/settings/prod.py

# Disable GZip for responses containing sensitive data
# Or use django-debreach
INSTALLED_APPS += ['debreach']

MIDDLEWARE = [
    # Thêm trước SecurityMiddleware
    'debreach.middleware.CSRFCryptMiddleware',
    'debreach.middleware.RandomCommentMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # ...
]

# Hoặc disable gzip cho authenticated responses
# Trong nginx config:
# gzip_types text/plain text/css application/json;
# Không compress text/html cho authenticated users
```

---

### 🟢 MỨC ĐỘ NGHIÊM TRỌNG THẤP

#### SEC-009: Debug Information Exposure Risk

**📍 Vị trí:** `config/settings/dev.py` (dòng 43)

**❌ Mã hiện tại:**
```python
CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"].append("'unsafe-inline'")
CONTENT_SECURITY_POLICY["DIRECTIVES"]["style-src"].append("'unsafe-inline'")
```

**❓ Vấn đề:** `unsafe-inline` giảm bảo mật CSP đáng kể, dù chỉ trong dev.

**✅ Giải pháp:**
```python
# Chỉ cho phép unsafe-inline khi thực sự cần
if env.bool('ALLOW_UNSAFE_INLINE', default=False):
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"].append("'unsafe-inline'")
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["style-src"].append("'unsafe-inline'")
```

---

#### SEC-010: Missing Security Headers cho API Responses

**📍 Vị trí:** `backends/tenancy/middleware.py`

**❓ Vấn đề:** Security headers chỉ apply cho HTML responses, không cho API JSON responses.

**✅ Giải pháp:**
```python
def _add_security_headers(self, response: HttpResponse) -> None:
    """Add security headers to ALL responses."""
    for header, value in self.SECURITY_HEADERS.items():
        if header not in response:
            response[header] = value
    
    # Thêm headers cho API responses
    content_type = response.get('Content-Type', '')
    if 'application/json' in content_type:
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store'
```

---

#### SEC-011: Verbose Error Messages trong Validators

**📍 Vị trí:** `backends/audit_logs/utils/sanitizer.py`

**❌ Mã hiện tại:**
```python
logger.warning(
    "XSS ATTEMPT blocked: %s = %s", field_name, original[:100]
)
```

**❓ Vấn đề:** Log chứa payload có thể giúp attacker tinh chỉnh attack.

**✅ Giải pháp:**
```python
import hashlib

logger.warning(
    "XSS ATTEMPT blocked: field=%s hash=%s length=%d", 
    field_name, 
    hashlib.sha256(original.encode()).hexdigest()[:8],
    len(original)
)
```

---

#### SEC-012: Missing Rate Limit cho Login Page

**📍 Vị trí:** `config/settings/base.py`

**❓ Vấn đề:** Mặc dù có django-axes, rate limit allauth chỉ 5/minute có thể quá cao cho login.

**✅ Giải pháp:**
```python
# Giảm rate limit cho login
ACCOUNT_RATE_LIMITS = {
    "change_password": "3/m/user",
    "reset_password": "5/m/ip",
    "reset_password_email": "3/m/ip",
    "reset_password_from_key": "10/m/ip",
    "login_failed": "3/m/ip",  # Giảm từ 5 xuống 3
    "login": "5/m/ip",  # Thêm rate limit cho login attempts
}
```

---

#### SEC-013: Potential Path Traversal trong File Operations

**📍 Vị trí:** Nếu có file upload/download

**✅ Giải pháp chung:**
```python
import os
from pathlib import Path

def safe_join(base_dir: str, filename: str) -> str:
    """Safely join path, preventing directory traversal."""
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()
    
    # Đảm bảo target vẫn trong base_dir
    if not str(target).startswith(str(base)):
        raise ValueError("Directory traversal attempt detected")
    
    return str(target)
```

---

#### SEC-014: Missing Account Enumeration Protection

**📍 Vị trí:** Password reset flow

**✅ Giải pháp:**
```python
# Đảm bảo response giống nhau cho cả valid/invalid email
# config/settings/base.py

# Allauth đã có setting này, đảm bảo enabled
ACCOUNT_PREVENT_ENUMERATION = True
```

---

## VẤN ĐỀ HIỆU SUẤT (BOTTLENECK)

### ⚡ PERF-001: N+1 Query trong Permission Loading

**📍 Vị trí:** `backends/tenancy/utils/tenancy_utils.py` (dòng 62-80)

**❌ Mã hiện tại:**
```python
memberships = StudyMembership.objects.filter(
    user=user, study=study, is_active=True
).select_related('group').prefetch_related(
    Prefetch(
        'group__permissions',
        queryset=Permission.objects.filter(
            content_type__app_label=app_label
        ).only('codename', 'content_type_id')
    )
)

for membership in memberships:
    for perm in membership.group.permissions.all():
        if perm.content_type.app_label == app_label:  # N+1 here!
            permissions.add(perm.codename)
```

**❓ Vấn đề:** `perm.content_type` gây N+1 query vì không được prefetch.

**✅ Giải pháp:**
```python
@classmethod
def get_user_permissions(cls, user, study) -> Set[str]:
    """Get user permissions - optimized to avoid N+1."""
    if not user or not study:
        return set()
    
    cache_key = cls._cache_key('perms', user.pk, study.pk)
    permissions = cache.get(cache_key)
    
    if permissions is not None:
        return permissions
    
    try:
        from backends.tenancy.models import StudyMembership
        
        app_label = f'study_{study.code.lower()}'
        
        # Single query với proper prefetch
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
        logger.error(f"Error getting permissions: {type(e).__name__}")
        permissions = set()
    
    return permissions
```

**📊 Impact:** Giảm từ O(n*m) queries xuống O(1) query.

---

### ⚡ PERF-002: Cache Key Generation Overhead

**📍 Vị trí:** `backends/tenancy/utils/tenancy_utils.py` (dòng 38-43)

**❌ Mã hiện tại:**
```python
@classmethod
def _cache_key(cls, *parts) -> str:
    key = '_'.join(str(p) for p in parts)
    if len(key) > 200:
        key = hashlib.sha256(key.encode()).hexdigest()[:32]
    return f"{cls.CACHE_PREFIX}{key}"
```

**❓ Vấn đề:** SHA256 hash cho mỗi long key là overhead không cần thiết.

**✅ Giải pháp:**
```python
import xxhash  # Faster hash library

@classmethod
def _cache_key(cls, *parts) -> str:
    """Generate cache key with fast hashing."""
    key = '_'.join(str(p) for p in parts)
    if len(key) > 200:
        # xxhash nhanh hơn SHA256 ~10x
        key = xxhash.xxh64(key.encode()).hexdigest()[:16]
    return f"{cls.CACHE_PREFIX}{key}"
```

**Hoặc đơn giản hơn:**
```python
@classmethod  
def _cache_key(cls, *parts) -> str:
    """Generate cache key - simple and fast."""
    # Với parts thường ngắn, join trực tiếp nhanh nhất
    return f"{cls.CACHE_PREFIX}{'_'.join(map(str, parts))}"
```

---

### ⚡ PERF-003: Regex Compilation trong Hot Path

**📍 Vị trí:** `backends/tenancy/middleware.py` (dòng 57-66)

**✅ Đã tốt:** Regex patterns được compile ở class level. ✅

---

### ⚡ PERF-004: Missing Database Indexes

**📍 Vị trí:** `backends/tenancy/models/study.py`

**❓ Vấn đề:** Một số queries thường xuyên có thể thiếu index.

**✅ Giải pháp:**
```python
# backends/tenancy/models/study.py

class StudyMembership(models.Model):
    # ... existing fields
    
    class Meta:
        db_table = 'study_membership'
        indexes = [
            # Composite index cho common query patterns
            models.Index(
                fields=['user', 'study', 'is_active'],
                name='idx_membership_user_study_active'
            ),
            models.Index(
                fields=['study', 'is_active'],
                name='idx_membership_study_active'
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study'],
                name='unique_user_study_membership'
            ),
        ]
```

---

### ⚡ PERF-005: Excessive Session Writes

**📍 Vị trí:** `backends/tenancy/middleware.py` (dòng 282-286)

**❌ Mã hiện tại:**
```python
def _update_session(self, request: HttpRequest, study: Study) -> None:
    request.session[self.STUDY_ID_KEY] = study.pk
    request.session[self.STUDY_CODE_KEY] = study.code
    request.session[self.STUDY_DB_KEY] = study.db_name
    request.session.modified = True  # Forces session save
```

**❓ Vấn đề:** Session write mỗi request nếu study context thay đổi.

**✅ Giải pháp:**
```python
def _update_session(self, request: HttpRequest, study: Study) -> None:
    """Update session only if values changed."""
    changed = False
    
    if request.session.get(self.STUDY_ID_KEY) != study.pk:
        request.session[self.STUDY_ID_KEY] = study.pk
        changed = True
    
    if request.session.get(self.STUDY_CODE_KEY) != study.code:
        request.session[self.STUDY_CODE_KEY] = study.code
        changed = True
    
    if request.session.get(self.STUDY_DB_KEY) != study.db_name:
        request.session[self.STUDY_DB_KEY] = study.db_name
        changed = True
    
    if changed:
        request.session.modified = True
```

---

### ⚡ PERF-006: Connection Pool Không Tối Ưu

**📍 Vị trí:** `config/settings/base.py` (dòng 121)

**❌ Mã hiện tại:**
```python
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
```

**❓ Vấn đề:** 
- 60s có thể quá dài cho high-traffic
- Không có connection pooling cho study databases

**✅ Giải pháp:**
```python
# config/settings/base.py

# Tuned connection settings
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=30)  # Giảm xuống 30s
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# Thêm cho production
if not DEBUG:
    # Sử dụng PgBouncer hoặc django-db-connection-pool
    DATABASES["default"]["OPTIONS"] = {
        "MAX_CONNS": 20,  # Max connections per process
        "OPTIONS": "-c statement_timeout=30000",  # 30s query timeout
    }
```

**Recommend:** Sử dụng PgBouncer cho connection pooling ở production:
```yaml
# docker-compose.yml
pgbouncer:
  image: bitnami/pgbouncer:latest
  environment:
    - PGBOUNCER_DATABASE=resync
    - PGBOUNCER_POOL_MODE=transaction
    - PGBOUNCER_MAX_CLIENT_CONN=100
    - PGBOUNCER_DEFAULT_POOL_SIZE=20
```

---

### ⚡ PERF-007: Audit Log Detail Bulk Creation

**📍 Vị trí:** `backends/audit_logs/utils/decorators.py` (dòng 395-405)

**✅ Đã tốt:** Sử dụng `bulk_create()` cho audit details. ✅

---

### ⚡ PERF-008: Missing Query Optimization cho Study List

**📍 Vị trí:** `backends/api/base/views.py` (khi load studies)

**✅ Giải pháp:**
```python
# backends/api/base/services/study_service.py

@classmethod
def get_user_studies(cls, user, query: str = None):
    """Get user's accessible studies - optimized."""
    from backends.tenancy.models import Study, StudyMembership
    
    # Single query với annotate thay vì N queries
    studies = Study.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
    ).select_related(
        'created_by'
    ).prefetch_related(
        Prefetch(
            'memberships',
            queryset=StudyMembership.objects.filter(
                user=user, is_active=True
            ).select_related('group'),
            to_attr='user_membership'
        )
    ).distinct()
    
    if query:
        studies = studies.filter(
            Q(code__icontains=query) |
            Q(name_vi__icontains=query) |
            Q(name_en__icontains=query)
        )
    
    return studies.order_by('code')
```

---

### ⚡ PERF-009: Template Caching

**📍 Vị trí:** `config/settings/prod.py` (dòng 91-100)

**✅ Đã tốt:** Template caching được enable trong production. ✅

---

### ⚡ PERF-010: Redis Connection Pool

**📍 Vị trí:** `config/settings/base.py` (dòng 142-157)

**✅ Đã tốt:** Connection pool được configure với max_connections và timeout. ✅

**Khuyến nghị thêm:**
```python
# Thêm health check cho Redis
CACHES = {
    "default": {
        # ... existing config
        "OPTIONS": {
            # ... existing options
            "SOCKET_KEEPALIVE": True,  # Keep connections alive
            "RETRY_ON_TIMEOUT": True,   # Auto retry
            "HEALTH_CHECK_INTERVAL": 30,  # Check every 30s
        },
    }
}
```

---

## ĐIỂM TÍCH CỰC

### ✅ Security Best Practices Đã Áp Dụng

1. **Argon2 Password Hashing** - Sử dụng Argon2 (winner of PHC) làm default hasher
2. **CSRF Protection** - CSRF với HTTPOnly và SameSite=Strict
3. **Content Security Policy** - CSP đầy đủ với nonce support
4. **Brute Force Protection** - Django-axes với intelligent lockout
5. **Rate Limiting** - Multi-layer rate limiting (allauth + middleware)
6. **Input Sanitization** - Comprehensive XSS, SQL injection protection
7. **Audit Logging** - HMAC-SHA256 checksums cho integrity
8. **Session Security** - HTTPOnly, Secure cookies, proper expiry
9. **Security Headers** - X-Frame-Options, X-Content-Type-Options, etc.
10. **SQL Injection Prevention** - Django ORM usage, no raw SQL

### ✅ Performance Best Practices Đã Áp Dụng

1. **Compiled Regex Patterns** - Class-level compiled patterns
2. **Database Connection Health Checks** - CONN_HEALTH_CHECKS = True
3. **Caching Strategy** - Two-layer caching (request + Django cache)
4. **Select Related / Prefetch Related** - Proper query optimization
5. **Bulk Operations** - bulk_create() cho audit details
6. **Lazy Loading** - SimpleLazyObject cho expensive operations
7. **Index Usage** - Proper database indexes on key fields
8. **Static File Optimization** - WhiteNoise với long cache headers

---

## HƯỚNG DẪN KHẮC PHỤC CHI TIẾT

### Bước 1: Security Fixes (Ưu tiên cao)

```bash
# 1. Fix CSP nonce cho external scripts
# File: frontends/templates/base.html
# Thay đổi: Thêm nonce="{{ request.csp_nonce }}" cho tất cả scripts

# 2. Fix rate limiting race condition
# File: backends/tenancy/middleware.py
# Thay đổi: Sử dụng cache.incr() thay vì get/set

# 3. Fix session fixation
# File: backends/tenancy/signals.py
# Thay đổi: Sử dụng session.flush() thay vì cycle_key()

# 4. Update password policy
# File: config/settings/security.py
# Thay đổi: min_length = 12, thêm PasswordComplexityValidator
```

### Bước 2: Performance Fixes

```bash
# 1. Optimize permission queries
# File: backends/tenancy/utils/tenancy_utils.py
# Thay đổi: Single query với proper joins

# 2. Add missing indexes
# File: backends/tenancy/models/*.py
# Thay đổi: Thêm composite indexes

# 3. Optimize session writes
# File: backends/tenancy/middleware.py
# Thay đổi: Only write if changed
```

### Bước 3: Testing

```bash
# Run security tests
python manage.py check --deploy

# Run performance profiling
python manage.py shell
>>> from django.test.utils import override_settings
>>> # Test query counts
```

---

## CHECKLIST TRIỂN KHAI

### Pre-Deployment Checklist

- [ ] **SEC-001:** Thêm CSP nonce cho external scripts
- [ ] **SEC-002:** Update error logging để không leak sensitive info
- [ ] **SEC-003:** Implement atomic rate limiting
- [ ] **SEC-004:** Update password minimum length to 12
- [ ] **SEC-005:** Implement full session fixation protection
- [ ] **SEC-006:** Configure TRUSTED_PROXY_IPS
- [ ] **SEC-007:** Add timing-safe checksum comparison
- [ ] **PERF-001:** Optimize permission queries
- [ ] **PERF-004:** Add database indexes
- [ ] **PERF-005:** Optimize session writes

### Monitoring Setup

```python
# Thêm monitoring cho security events
# config/settings/logging.py

LOGGING['loggers']['security'] = {
    'handlers': ['file_security', 'console'],
    'level': 'WARNING',
    'propagate': False,
}

# Metrics to monitor:
# - Rate limit hits per minute
# - Failed login attempts
# - Audit log integrity failures
# - Slow query counts (>1000ms)
# - Database connection pool usage
```

### Regular Security Tasks

1. **Weekly:** Review security logs
2. **Monthly:** Update dependencies (`pip-audit`)
3. **Quarterly:** Penetration testing
4. **Yearly:** Full security audit

---

## KẾT LUẬN

Dự án ResSynt có nền tảng bảo mật và hiệu suất khá tốt với nhiều best practices đã được áp dụng. Các vấn đề được phát hiện chủ yếu là cải tiến bổ sung thay vì lỗ hổng nghiêm trọng.

**Ưu tiên khắc phục:**
1. 🔴 **Ngay lập tức:** SEC-001, SEC-003 (CSP và Race condition)
2. 🟡 **Trong tuần:** SEC-004, SEC-005, SEC-006
3. 🟢 **Khi có thời gian:** PERF optimizations

**Điểm số tổng thể: 8/10** - Dự án đã implement nhiều security controls tốt, cần một số cải tiến để đạt production-grade security.

---

*Báo cáo này được tạo tự động bởi GitHub Copilot AI Auditor. Vui lòng review và validate từng recommendation trước khi apply.*
