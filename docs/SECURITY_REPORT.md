# Báo Cáo Kiến Trúc Bảo Mật Hệ Thống ResSynt

**Ngày tạo:** 15/01/2026  
**Phiên bản hệ thống:** 1.0.0  
**Loại tài liệu:** Security Architecture Report  
**Hệ thống:** ResSynt - Research Data Management Platform  
**Framework:** Django 5.x + Python 3.14

---

## Mục Lục

1. [Tổng Quan Kiến Trúc Bảo Mật](#1-tổng-quan-kiến-trúc-bảo-mật)
2. [Layer 1: Transport Security (HTTPS/HSTS)](#2-layer-1-transport-security-httpshsts)
3. [Layer 2: Security Headers & Content Security Policy](#3-layer-2-security-headers--content-security-policy)
4. [Layer 3: Rate Limiting & Brute-Force Protection](#4-layer-3-rate-limiting--brute-force-protection)
5. [Layer 4: Authentication & Session Security](#5-layer-4-authentication--session-security)
6. [Layer 5: Multi-Tenancy & Database Isolation](#6-layer-5-multi-tenancy--database-isolation)
7. [Layer 6: Role-Based Access Control (RBAC)](#7-layer-6-role-based-access-control-rbac)
8. [Layer 7: Data Encryption](#8-layer-7-data-encryption)
9. [Layer 8: Audit Logging & Integrity Verification](#9-layer-8-audit-logging--integrity-verification)
10. [Bảo Vệ Chống Các Lỗ Hổng Phổ Biến](#10-bảo-vệ-chống-các-lỗ-hổng-phổ-biến)
11. [Thư Viện & Thuật Toán Bảo Mật](#11-thư-viện--thuật-toán-bảo-mật)
12. [Tổng Kết & Khuyến Nghị](#12-tổng-kết--khuyến-nghị)

---

## 1. Tổng Quan Kiến Trúc Bảo Mật

Hệ thống ResSynt triển khai kiến trúc bảo mật **Defense in Depth** (Bảo vệ theo chiều sâu) với **8 lớp bảo mật** độc lập, kết hợp multi-tenancy với database isolation, role-based access control (RBAC), và audit logging toàn diện.

### 1.1 Sơ Đồ Kiến Trúc Bảo Mật

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                       │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: TRANSPORT SECURITY                                            │
│  ├─ HTTPS (TLS 1.2+)                                                    │
│  ├─ HSTS (HTTP Strict Transport Security)                               │
│  └─ Secure Cookies                                                       │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: SECURITY HEADERS & CSP                                        │
│  ├─ Content Security Policy (CSP) với Nonce                             │
│  ├─ X-Frame-Options: DENY                                                │
│  ├─ X-Content-Type-Options: nosniff                                      │
│  └─ Referrer-Policy, Permissions-Policy                                  │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: RATE LIMITING & BRUTE-FORCE PROTECTION                        │
│  ├─ Django-Axes (7 failed attempts → permanent lock)                    │
│  ├─ Allauth Rate Limits (5 failed/min/IP)                               │
│  └─ Custom Rate Limiting (60 req/min authenticated)                     │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: AUTHENTICATION & SESSION                                       │
│  ├─ Argon2 Password Hashing (Memory-Hard)                               │
│  ├─ Session Regeneration (Anti-Fixation)                                │
│  ├─ CSRF Protection (Double Submit Cookie + Sessions)                   │
│  └─ Password Validators                                                  │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: MULTI-TENANCY & DATABASE ISOLATION                            │
│  ├─ Separate Database per Study                                          │
│  ├─ Schema Separation (data/logging)                                     │
│  ├─ Thread-Local Database Context                                        │
│  └─ Database Router (TenantRouter)                                       │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 6: RBAC & SITE-BASED AUTHORIZATION                               │
│  ├─ Role Templates (5 roles)                                             │
│  ├─ Django Groups & Permissions                                          │
│  ├─ Site-Level Access Control                                            │
│  └─ StudyMembership Model                                                │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 7: DATA ENCRYPTION                                                │
│  ├─ Fernet Symmetric Encryption (AES-128-CBC + HMAC-SHA256)             │
│  ├─ RSA Asymmetric Keys (Backup Signatures)                             │
│  └─ Backup Encryption                                                    │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 8: AUDIT LOGGING & INTEGRITY                                      │
│  ├─ Immutable Audit Logs                                                 │
│  ├─ HMAC-SHA256 Checksum                                                 │
│  ├─ Field-Level Change Tracking                                          │
│  └─ Integrity Verification                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Các File Cấu Hình Bảo Mật Chính

| File | Mô tả |
|------|-------|
| `config/settings/base.py` | Cấu hình chung (AXES, Session, Auth) |
| `config/settings/security.py` | CSP, CSRF, Password Validators |
| `config/settings/prod.py` | HTTPS, HSTS, Production hardening |
| `backends/tenancy/middleware.py` | Security headers, Rate limiting, Study routing |
| `backends/tenancy/db_router.py` | Database isolation logic |
| `backends/tenancy/signals.py` | Auth events, Security alerts |
| `backends/audit_logs/models/base.py` | Audit logging với checksum |

---

## 2. Layer 1: Transport Security (HTTPS/HSTS)

### 2.1 Mô Tả

Transport Layer Security (TLS) bảo vệ dữ liệu truyền tải giữa client và server, chống lại các cuộc tấn công Man-in-the-Middle (MITM).

### 2.2 Cấu Hình

**File:** `config/settings/prod.py`

```python
# HTTPS Enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookie Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000       # 1 năm
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 2.3 Chi Tiết Kỹ Thuật

| Setting | Giá Trị | Mục Đích |
|---------|---------|----------|
| `SECURE_SSL_REDIRECT` | `True` | Tự động redirect HTTP → HTTPS (301 Redirect) |
| `SECURE_HSTS_SECONDS` | `31536000` | Browser nhớ HTTPS 1 năm |
| `SECURE_HSTS_PRELOAD` | `True` | Đăng ký vào HSTS Preload List của trình duyệt |
| `SESSION_COOKIE_SECURE` | `True` | Cookie session chỉ gửi qua HTTPS |

### 2.4 Threats Được Chống

- **Man-in-the-Middle (MITM)**: TLS mã hóa traffic
- **SSL Stripping**: HSTS buộc browser dùng HTTPS
- **Cookie Theft qua HTTP**: Secure flag chặn gửi cookie qua HTTP

---

## 3. Layer 2: Security Headers & Content Security Policy

### 3.1 Security Headers

**File:** `backends/tenancy/middleware.py`

```python
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}
```

| Header | Giá Trị | Mục Đích |
|--------|---------|----------|
| `X-Content-Type-Options` | `nosniff` | Chặn MIME-type sniffing (XSS via content-type confusion) |
| `X-Frame-Options` | `DENY` | Chặn embedding trong iframe (Clickjacking) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Hạn chế leak URL trong Referrer header |
| `Permissions-Policy` | Disable sensitive APIs | Vô hiệu hóa camera, microphone, geolocation |

### 3.2 Content Security Policy (CSP)

**File:** `config/settings/security.py`

**Thư viện sử dụng:** `django-csp` (version 4.0+)

```python
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],                    # Mặc định chỉ cho phép same-origin
        "script-src": [
            SELF,
            "https://cdn.jsdelivr.net",           # CDN scripts
            "https://ajax.googleapis.com",
        ],
        "style-src": [
            SELF,
            "https://fonts.googleapis.com",
            "https://cdn.jsdelivr.net",
        ],
        "font-src": [SELF, "https://fonts.gstatic.com", "data:"],
        "img-src": [SELF, "data:", "https:"],
        "connect-src": [SELF],                    # AJAX/Fetch requests
        "frame-ancestors": ["'none'"],            # Không cho phép iframe
        "base-uri": [SELF],                       # Chống base tag injection
        "form-action": [SELF],                    # Form chỉ submit về cùng origin
    },
}

# Nonce-based CSP
CSP_INCLUDE_NONCE_IN = ["script-src", "style-src"]
```

### 3.3 CSP Nonce Mechanism

**Cách hoạt động:**
1. Server sinh random nonce cho mỗi request
2. Nonce được thêm vào CSP header: `script-src 'nonce-abc123'`
3. Inline scripts phải có attribute: `<script nonce="abc123">`
4. Scripts không có nonce sẽ bị block

**Chống được:**
- Inline Script Injection (Stored/Reflected XSS)
- Third-party Script Injection

### 3.4 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Cross-Site Scripting (XSS)** | CSP chặn inline scripts và third-party scripts |
| **Clickjacking** | `X-Frame-Options: DENY` và `frame-ancestors: 'none'` |
| **MIME Sniffing** | `X-Content-Type-Options: nosniff` |
| **Data Exfiltration** | `connect-src: 'self'` chặn AJAX đến domains khác |

---

## 4. Layer 3: Rate Limiting & Brute-Force Protection

### 4.1 Kiến Trúc Rate Limiting 3 Lớp

```
┌───────────────────────────────────────────────────────────────┐
│  LỚP 1: ALLAUTH RATE LIMITS (Soft Limit)                      │
│  - 5 failed logins/phút/IP → Thông báo rate limit            │
│  - 10 password resets/phút/IP                                 │
└───────────────────────────────────┬───────────────────────────┘
                                    │ (nếu tiếp tục)
                                    ▼
┌───────────────────────────────────────────────────────────────┐
│  LỚP 2: DJANGO-AXES (Hard Limit)                              │
│  - 7 failed attempts → KHÓA VĨNH VIỄN                         │
│  - Khóa theo combo: username + IP                             │
│  - Cần admin mở khóa thủ công                                 │
└───────────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────┐
│  LỚP 3: CUSTOM RATE LIMITING (API/Forms)                      │
│  - Anonymous: 10 req/phút                                     │
│  - Authenticated: 60 req/phút                                 │
│  - Áp dụng cho: POST, PUT, DELETE, PATCH                      │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 Django-AXES Configuration

**File:** `config/settings/base.py`

**Thư viện:** `django-axes` (version 8.0.0)

```python
# Core Settings
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 7              # Số lần thất bại tối đa
AXES_COOLOFF_TIME = None            # None = khóa vĩnh viễn

# Lockout Strategy
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]  # Khóa theo combo
AXES_RESET_ON_SUCCESS = False       # Không auto-reset khi login thành công

# Storage
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

# Form Field Mapping
AXES_USERNAME_FORM_FIELD = "login"
AXES_PASSWORD_FORM_FIELD = "password"
AXES_SENSITIVE_PARAMETERS = ["password"]  # Không log password

# Custom Lockout Response
AXES_LOCKOUT_CALLABLE = "backends.api.base.account.lockout.lockout_response"
```

### 4.3 Allauth Rate Limits

**File:** `config/settings/base.py`

```python
ACCOUNT_RATE_LIMITS = {
    "change_password": "5/m/user",
    "reset_password": "10/m/ip",
    "reset_password_email": "5/m/ip",
    "reset_password_from_key": "20/m/ip",
    "login_failed": "5/m/ip",         # Layer đầu tiên
}
```

### 4.4 Custom Rate Limiting (Middleware)

**File:** `backends/tenancy/middleware.py`

```python
def _check_rate_limit(self, request):
    # Skip cho safe methods
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    
    # Skip cho superusers
    if request.user.is_authenticated and request.user.is_superuser:
        return None
    
    # Rate limits
    if request.user.is_authenticated:
        max_requests = 60   # 60 requests/phút
    else:
        max_requests = 10   # 10 requests/phút
    
    # Check & increment counter (Redis/Cache)
    count = cache.get(key, 0)
    if count >= max_requests:
        return HttpResponse('Too many requests', status=429)
    
    cache.set(key, count + 1, window=60)
```

### 4.5 Security Alert (Async via Celery)

Khi có lockout, hệ thống gửi alert qua Celery:

```python
@receiver(user_locked_out)
def handle_axes_lockout(request, credentials, **kwargs):
    send_security_alert.delay(
        alert_type='user_lockout',
        details={
            'username': username,
            'ip_address': ip_address,
            'timestamp': timestamp,
        }
    )
```

### 4.6 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Brute-Force Attack** | AXES khóa sau 7 attempts |
| **Credential Stuffing** | Rate limiting 5/phút |
| **Password Spraying** | Combo username+IP tracking |
| **API Abuse** | 60 req/phút limit |

---

## 5. Layer 4: Authentication & Session Security

### 5.1 Password Hashing

**File:** `config/settings/security.py`

**Thuật toán sử dụng (theo thứ tự ưu tiên):**

```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",      # Mạnh nhất
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
```

#### 5.1.1 Argon2 (Primary Hasher)

**Đặc điểm:**
- **Memory-Hard Algorithm**: Chống GPU/ASIC attacks
- **Phiên bản:** Argon2id (hybrid của Argon2i và Argon2d)
- **Winner of Password Hashing Competition 2015**

**Parameters mặc định:**
- Memory: 102400 KB (100 MB)
- Time: 2 iterations
- Parallelism: 8 threads

**Ưu điểm so với bcrypt/PBKDF2:**
- Yêu cầu memory cao → khó brute-force với GPU farm
- Configurable resources (time, memory, parallelism)

#### 5.1.2 Các Hasher Backup

| Hasher | Thuật Toán | Use Case |
|--------|------------|----------|
| Scrypt | scrypt (Memory-Hard) | Backup nếu Argon2 không available |
| BCrypt SHA256 | bcrypt + SHA256 | Legacy compatibility |
| PBKDF2 | PBKDF2-HMAC-SHA256 | Django default |

### 5.2 Password Validators

**File:** `config/settings/security.py`

```python
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {
            "user_attributes": ("username", "first_name", "last_name", "email"),
            "max_similarity": 0.7,      # Cosine similarity threshold
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        # Uses list of 20,000 common passwords
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        # Blocks all-numeric passwords
    },
]
```

| Validator | Mô Tả |
|-----------|-------|
| `UserAttributeSimilarityValidator` | Chặn password giống username/email |
| `MinimumLengthValidator` | Tối thiểu 8 ký tự |
| `CommonPasswordValidator` | Chặn 20,000 passwords phổ biến nhất |
| `NumericPasswordValidator` | Chặn passwords toàn số |

### 5.3 Session Security

**File:** `config/settings/base.py`

```python
# Session Engine
SESSION_ENGINE = "django.contrib.sessions.backends.db"  # Database-backed

# Cookie Settings
SESSION_COOKIE_NAME = "resync_sessionid"
SESSION_COOKIE_AGE = 28800              # 8 giờ
SESSION_COOKIE_HTTPONLY = True          # Chặn JavaScript access
SESSION_COOKIE_SECURE = True            # Chỉ gửi qua HTTPS
SESSION_COOKIE_SAMESITE = "Lax"         # Chống CSRF

# Session Behavior
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Hết session khi đóng browser
SESSION_SAVE_EVERY_REQUEST = False      # Performance optimization
```

### 5.4 Session Regeneration (Anti-Fixation)

**File:** `backends/tenancy/signals.py`

```python
@receiver(allauth_logged_in)
def handle_allauth_login(request, user, **kwargs):
    # Regenerate session ID để chống session fixation
    if hasattr(request, 'session'):
        request.session.cycle_key()
```

**Session Fixation Attack:**
1. Attacker tạo session và gửi session ID cho victim
2. Victim đăng nhập với session ID đó
3. Attacker sử dụng session ID để hijack session

**Giải pháp:** `cycle_key()` tạo session ID mới sau login thành công.

### 5.5 CSRF Protection

**File:** `config/settings/security.py`

```python
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_USE_SESSIONS = True        # Store CSRF token in session (không phải cookie)
CSRF_COOKIE_AGE = None          # Session-only CSRF token
```

**Cơ chế Double Submit Cookie:**
1. Server gửi CSRF token trong cookie + form hidden field
2. Request phải có cả hai và phải match
3. Attacker không thể đọc cookie từ JavaScript (do Same-Origin Policy)

### 5.6 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Password Cracking** | Argon2 memory-hard, 100MB per hash |
| **Session Fixation** | `session.cycle_key()` regeneration |
| **Session Hijacking** | HttpOnly, Secure, SameSite cookies |
| **CSRF** | Double Submit + Session-based token |
| **Weak Passwords** | 4 validators, common password list |

---

## 6. Layer 5: Multi-Tenancy & Database Isolation

### 6.1 Kiến Trúc Database

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MANAGEMENT DATABASE (default)                        │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  - auth_user (Users)                                                │ │
│  │  - django_session (Sessions)                                        │ │
│  │  - axes_accessattempt (Login tracking)                              │ │
│  │  - study_information (Study metadata)                               │ │
│  │  - study_memberships (User-Study-Role mapping)                      │ │
│  │  - study_sites, study_site_links                                    │ │
│  │  - django_content_type, auth_permission, auth_group                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ db_study_43en   │ │ db_study_44en   │ │ db_study_xxx    │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │
│ │data schema  │ │ │ │data schema  │ │ │ │data schema  │ │
│ │ - CRF tables│ │ │ │ - CRF tables│ │ │ │ - CRF tables│ │
│ │ - Patient   │ │ │ │ - Patient   │ │ │ │ - Patient   │ │
│ │ - Visit     │ │ │ │ - Visit     │ │ │ │ - Visit     │ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │
│ │logging      │ │ │ │logging      │ │ │ │logging      │ │
│ │ - audit_log │ │ │ │ - audit_log │ │ │ │ - audit_log │ │
│ │ - details   │ │ │ │ - details   │ │ │ │ - details   │ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 6.2 Database Router

**File:** `backends/tenancy/db_router.py`

```python
class TenantRouter:
    """Multi-tenant database router."""
    
    # Apps trong management database
    MANAGEMENT_APPS = frozenset({
        'admin', 'auth', 'contenttypes', 'sessions',
        'messages', 'staticfiles', 'tenancy', 'axes',
        'usersessions', 'sites', 'account',
    })
    
    # Apps trong study databases
    STUDY_APPS = frozenset({'studies'})
    
    def db_for_read(self, model, **hints):
        return self._get_db_for_model(model)
    
    def db_for_write(self, model, **hints):
        return self._get_db_for_model(model)
    
    def _get_db_for_model(self, model):
        app_label = model._meta.app_label
        
        if app_label in self.MANAGEMENT_APPS:
            return 'default'
        
        if app_label in self.STUDY_APPS or app_label.startswith('study_'):
            return get_current_db()  # Thread-local database
        
        return get_current_db()
    
    def allow_relation(self, obj1, obj2, **hints):
        """Chỉ cho phép relations trong cùng database."""
        db1 = self._get_db_for_model(obj1.__class__)
        db2 = self._get_db_for_model(obj2.__class__)
        return db1 == db2
```

### 6.3 Thread-Local Database Context

**File:** `backends/tenancy/db_router.py`

```python
import threading

_thread_local = threading.local()

def get_current_db() -> str:
    """Get current database for this thread."""
    return getattr(_thread_local, 'db', 'default')

def set_current_db(db_alias: str) -> None:
    """Set current database for this thread."""
    _thread_local.db = db_alias if db_alias else 'default'

def clear_current_db() -> None:
    """Clear current database context."""
    if hasattr(_thread_local, 'db'):
        del _thread_local.db
```

**Luồng xử lý request:**

```
1. Request đến: /studies/43EN/patients/
                      │
2. Middleware extract code: "43EN"
                      │
3. Validate format: ^[A-Z0-9_]{2,20}$  ← Chống injection
                      │
4. Check membership: StudyMembership.objects.get(user=user, study=study)
                      │
5. Set database: set_current_db('db_study_43en')
                      │
6. Process request với ORM automatic routing
                      │
7. Cleanup: clear_current_db()
```

### 6.4 Study Code Validation (Security)

**File:** `backends/tenancy/middleware.py`

```python
# Valid study code pattern
_valid_code_re = re.compile(r'^[A-Z0-9_]{2,20}$')

def _extract_study_code(self, path: str) -> Optional[str]:
    match = self._study_path_re.match(path)
    if not match:
        return None
    
    code = match.group('code').upper()
    
    # Security: validate code format
    if not self._valid_code_re.match(code):
        logger.warning(f"Invalid study code format: {code[:50]}")
        return None
    
    return code
```

**Chống được:**
- Path Traversal: `../../../etc/passwd`
- SQL Injection qua study code: `43EN'; DROP TABLE--`
- Command Injection: `43EN$(whoami)`

### 6.5 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Cross-Tenant Data Leak** | Separate database per study |
| **SQL Injection via tenant ID** | Strict regex validation |
| **Cross-database relations** | Router blocks cross-DB FK |
| **Thread confusion** | Thread-local storage |

---

## 7. Layer 6: Role-Based Access Control (RBAC)

### 7.1 Role Templates

**File:** `backends/tenancy/utils/role_manager.py`

```python
class RoleTemplate:
    ROLES = {
        "data_manager": {
            "display_name": "Data Manager",
            "description": "Full study access including user management.",
            "permissions": ["add", "change", "delete", "view"],
            "priority": 100,
            "is_privileged": True,
        },
        "research_manager": {
            "display_name": "Research Manager",
            "description": "Manages data entry and oversight.",
            "permissions": ["add", "change", "view"],
            "priority": 80,
        },
        "principal_investigator": {
            "display_name": "Principal Investigator",
            "description": "Leads the study with view access.",
            "permissions": ["view"],
            "priority": 70,
        },
        "research_monitor": {
            "display_name": "Research Monitor",
            "description": "Conducts study monitoring and review.",
            "permissions": ["view"],
            "priority": 60,
        },
        "research_staff": {
            "display_name": "Research Staff",
            "description": "Performs data entry and follow-up.",
            "permissions": ["add", "change", "view"],
            "priority": 50,
        },
    }
```

### 7.2 Permission Matrix

| Role | Add | Change | Delete | View |
|------|-----|--------|--------|------|
| Data Manager | ✅ | ✅ | ✅ | ✅ |
| Research Manager | ✅ | ✅ | ❌ | ✅ |
| Principal Investigator | ❌ | ❌ | ❌ | ✅ |
| Research Monitor | ❌ | ❌ | ❌ | ✅ |
| Research Staff | ✅ | ✅ | ❌ | ✅ |

### 7.3 StudyMembership Model

**File:** `backends/tenancy/models/permission.py`

```python
class StudyMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)  # Role
    
    # Site-level access control
    study_sites = models.ManyToManyField(StudySite, blank=True)
    can_access_all_sites = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study'],
                name='unique_user_study'  # 1 user = 1 role per study
            )
        ]
```

### 7.4 Site-Based Authorization

```python
# Trong middleware
site_info = TenancyUtils.get_user_site_access(request.user, study)
request.can_access_all_sites = site_info['can_access_all']
request.user_sites = site_info['sites']

# Trong view
def get_queryset(self):
    qs = super().get_queryset()
    
    if not self.request.can_access_all_sites:
        # Filter by user's sites
        qs = qs.filter(SITEID__in=self.request.user_sites)
    
    return qs
```

### 7.5 Permission Checking

**File:** `backends/tenancy/utils/tenancy_utils.py`

```python
class TenancyUtils:
    @classmethod
    def get_user_permissions(cls, user, study) -> Set[str]:
        """Get user permissions với caching."""
        cache_key = cls._cache_key('perms', user.pk, study.pk)
        permissions = cache.get(cache_key)
        
        if permissions is None:
            permissions = set()
            app_label = f'study_{study.code.lower()}'
            
            memberships = StudyMembership.objects.filter(
                user=user, study=study, is_active=True
            ).select_related('group').prefetch_related(
                'group__permissions'
            )
            
            for membership in memberships:
                for perm in membership.group.permissions.all():
                    if perm.content_type.app_label == app_label:
                        permissions.add(perm.codename)
            
            cache.set(cache_key, permissions, 300)  # 5 phút
        
        return permissions
    
    @classmethod
    def user_has_permission(cls, user, study, codename: str) -> bool:
        return codename in cls.get_user_permissions(user, study)
```

### 7.6 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Privilege Escalation** | Role-based với fixed templates |
| **Horizontal Access** | Site-based isolation |
| **Vertical Access** | Permission matrix enforcement |
| **Stale Permissions** | Cache invalidation on membership change |

---

## 8. Layer 7: Data Encryption

### 8.1 Field-Level Encryption

**File:** `config/settings/base.py`

**Thư viện:** `django-fernet-fields` hoặc `django-encrypted-model-fields`

```python
# Fernet encryption keys
FERNET_KEYS = [env("FIELD_ENCRYPTION_KEY")]

# Salt for encrypted_fields
SALT_KEY = env("SALT_KEY")
if not SALT_KEY:
    raise ValueError("SALT_KEY must be set")

# Backup encryption
BACKUP_ENCRYPTION_PASSWORD = env("BACKUP_ENCRYPTION_PASSWORD")
```

### 8.2 Fernet Encryption Details

**Thuật toán:** Fernet = AES-128-CBC + HMAC-SHA256

```
┌─────────────────────────────────────────────────────────────┐
│                    FERNET TOKEN FORMAT                       │
├─────────────────────────────────────────────────────────────┤
│  Version (1 byte) │ Timestamp (8 bytes) │ IV (16 bytes)    │
├─────────────────────────────────────────────────────────────┤
│              Ciphertext (variable)                          │
├─────────────────────────────────────────────────────────────┤
│                HMAC-SHA256 (32 bytes)                       │
└─────────────────────────────────────────────────────────────┘
```

**Properties:**
- **Confidentiality**: AES-128-CBC
- **Integrity**: HMAC-SHA256 (32 bytes)
- **Freshness**: Timestamp prevents replay attacks

### 8.3 RSA Keys for Backup Signatures

**File:** `backends/tenancy/models/user.py`

```python
class User(AbstractUser):
    # RSA PUBLIC KEY (for backup signature verification)
    public_key_pem = models.TextField(
        blank=True, null=True,
        help_text="User's RSA public key (PEM format)"
    )
    key_generated_at = models.DateTimeField(blank=True, null=True)
    key_last_rotated = models.DateTimeField(blank=True, null=True)
```

**Use Case:**
1. User sinh RSA key pair locally
2. Public key lưu vào database
3. Khi tạo backup, user sign với private key
4. Verify signature bằng public key để đảm bảo authenticity

### 8.4 Key Management

| Key Type | Storage | Rotation |
|----------|---------|----------|
| `FERNET_KEYS` | Environment variable | Hỗ trợ multiple keys |
| `SALT_KEY` | Environment variable | Fixed |
| `SECRET_KEY` | Environment (≥50 chars) | Careful rotation |
| RSA Keys | Database per user | User-initiated |

### 8.5 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Data at Rest Exposure** | Field-level Fernet encryption |
| **Backup Tampering** | RSA signature verification |
| **Key Compromise** | Key rotation support |
| **Rainbow Tables** | Salted encryption with SALT_KEY |

---

## 9. Layer 8: Audit Logging & Integrity Verification

### 9.1 Audit Log Model

**File:** `backends/audit_logs/models/base.py`

```python
class AbstractAuditLog(models.Model):
    """Immutable audit log entry."""
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('VIEW', 'View'),
    ]
    
    # WHO
    user_id = models.IntegerField(db_index=True)
    username = models.CharField(max_length=150, db_index=True)
    
    # WHEN
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # WHAT
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, db_index=True)
    patient_id = models.CharField(max_length=50, db_index=True)
    
    # WHERE
    SITEID = models.CharField(max_length=10, null=True, db_index=True)
    
    # WHY
    reason = models.TextField()
    
    # CONTEXT
    ip_address = models.GenericIPAddressField(null=True)
    session_id = models.CharField(max_length=40, null=True)
    
    # INTEGRITY
    checksum = models.CharField(max_length=64, editable=False)
    is_verified = models.BooleanField(default=True)
    
    class Meta:
        abstract = True
        default_permissions = ('add', 'view')  # Không có 'change', 'delete'
```

### 9.2 Immutability Enforcement

```python
def save(self, *args, **kwargs):
    """Prevent editing after creation."""
    if self.pk:
        raise PermissionDenied("Audit logs are immutable")
    
    # Generate checksum before save
    if not self.checksum:
        self.checksum = IntegrityChecker.generate_checksum(audit_data)
    
    super().save(*args, **kwargs)

def delete(self, *args, **kwargs):
    """Prevent deletion."""
    raise PermissionDenied("Audit logs cannot be deleted")
```

### 9.3 HMAC-SHA256 Checksum

**File:** `backends/audit_logs/utils/integrity.py`

```python
import hashlib
import hmac
import json
from django.conf import settings

class IntegrityChecker:
    @staticmethod
    def generate_checksum(audit_data: dict) -> str:
        """Generate HMAC-SHA256 checksum."""
        # Serialize data deterministically
        data_string = json.dumps(audit_data, sort_keys=True, default=str)
        
        # HMAC with secret key
        secret = settings.SECRET_KEY.encode()
        signature = hmac.new(
            secret,
            data_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature  # 64 hex characters
```

**Checksum Data Structure:**

```python
audit_data = {
    'user_id': 123,
    'username': 'john.doe',
    'action': 'UPDATE',
    'model_name': 'SCREENINGCASE',
    'patient_id': 'SCR-001',
    'timestamp': '2026-01-15 15:30:00+07:00',
    'old_data': {'field1': 'old_value'},
    'new_data': {'field1': 'new_value'},
    'reason': 'Correcting data entry error',
}
```

### 9.4 Integrity Verification

```python
def verify_integrity(self) -> bool:
    """Verify checksum hasn't been tampered."""
    # Reconstruct audit_data from stored values
    details = self.details.all()
    
    old_data = {d.field_name: d.old_value for d in details}
    new_data = {d.field_name: d.new_value for d in details}
    
    audit_data = {
        'user_id': self.user_id,
        'username': self.username,
        'action': self.action,
        'model_name': self.model_name,
        'patient_id': self.patient_id,
        'timestamp': str(self.timestamp),
        'old_data': old_data,
        'new_data': new_data,
        'reason': self.reason,
    }
    
    calculated = IntegrityChecker.generate_checksum(audit_data)
    return calculated == self.checksum
```

### 9.5 Per-Study Audit Tables

```python
# Factory pattern tạo models cho từng study
def create_audit_models(app_label: str):
    """Create AuditLog and AuditLogDetail for a study."""
    
    class AuditLogMeta:
        app_label = app_label
        db_table = 'logging"."audit_log'  # Schema separation
    
    AuditLog = type('AuditLog', (AbstractAuditLog,), {
        'Meta': AuditLogMeta,
        '__module__': f'backends.studies.{app_label}.models'
    })
    
    return AuditLog, AuditLogDetail

# Usage:
AuditLog, AuditLogDetail = create_audit_models('study_43en')
```

### 9.6 Threats Được Chống

| Threat | Giải Pháp |
|--------|-----------|
| **Log Tampering** | HMAC-SHA256 checksum |
| **Log Deletion** | Delete method raises PermissionDenied |
| **Log Modification** | Save method blocks updates |
| **Non-repudiation** | User ID, IP, timestamp, checksum |
| **Cross-study log access** | Per-study database + tables |

---

## 10. Bảo Vệ Chống Các Lỗ Hổng Phổ Biến

### 10.1 SQL Injection

#### 10.1.1 ORM Parameterization

Django ORM tự động escape tất cả user input:

```python
# SAFE - ORM handles escaping
Patient.objects.filter(name=user_input)

# GENERATED SQL:
# SELECT * FROM patient WHERE name = %s
# Parameters: ['user_input']
```

#### 10.1.2 Raw SQL Protection

```python
# SAFE - Parameterized query
cursor.execute(
    "SELECT * FROM patient WHERE name = %s",
    [user_input]
)

# UNSAFE - String formatting (KHÔNG SỬ DỤNG)
cursor.execute(f"SELECT * FROM patient WHERE name = '{user_input}'")
```

#### 10.1.3 Study Code Validation

```python
# Validate study code format trước khi dùng
_valid_code_re = re.compile(r'^[A-Z0-9_]{2,20}$')

if not _valid_code_re.match(study_code):
    raise ValidationError("Invalid study code")
```

### 10.2 Cross-Site Scripting (XSS)

#### 10.2.1 Template Auto-Escaping

Django templates tự động escape HTML:

```html
<!-- SAFE - Auto-escaped -->
<p>{{ user_input }}</p>
<!-- Output: &lt;script&gt;alert('xss')&lt;/script&gt; -->

<!-- UNSAFE - mark_safe (chỉ dùng với trusted content) -->
{{ user_input|safe }}
```

#### 10.2.2 Content Security Policy

```python
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "script-src": [SELF],  # Block inline scripts
        "style-src": [SELF],   # Block inline styles
    },
}
CSP_INCLUDE_NONCE_IN = ["script-src", "style-src"]
```

#### 10.2.3 HttpOnly Cookies

```python
SESSION_COOKIE_HTTPONLY = True  # JS không thể đọc session cookie
CSRF_COOKIE_HTTPONLY = True
```

### 10.3 Cross-Site Request Forgery (CSRF)

#### 10.3.1 CSRF Token

```html
<form method="post">
    {% csrf_token %}
    <input type="text" name="data">
    <button type="submit">Submit</button>
</form>
```

#### 10.3.2 SameSite Cookies

```python
CSRF_COOKIE_SAMESITE = "Strict"   # Không gửi cookie cross-site
SESSION_COOKIE_SAMESITE = "Lax"   # Cho phép safe navigation
```

#### 10.3.3 Logout Protection

```python
ACCOUNT_LOGOUT_ON_GET = False  # Require POST for logout
```

### 10.4 Clickjacking

```python
# Django middleware
X_FRAME_OPTIONS = "DENY"

# CSP
"frame-ancestors": ["'none'"]
```

### 10.5 Session Attacks

| Attack | Protection |
|--------|------------|
| **Session Fixation** | `session.cycle_key()` sau login |
| **Session Hijacking** | Secure, HttpOnly, SameSite cookies |
| **Session Prediction** | Django random session ID (256 bits) |
| **Session Timeout** | 8 giờ max age, expire on browser close |

### 10.6 Password Attacks

| Attack | Protection |
|--------|------------|
| **Brute Force** | AXES (7 attempts → lock) |
| **Credential Stuffing** | Rate limit 5/min/IP |
| **Rainbow Tables** | Argon2 with random salt |
| **Dictionary Attack** | CommonPasswordValidator |

### 10.7 Injection Attacks Summary

| Injection Type | Protection |
|----------------|------------|
| **SQL Injection** | ORM parameterization, input validation |
| **LDAP Injection** | N/A (không sử dụng LDAP) |
| **XPath Injection** | N/A (không sử dụng XPath) |
| **Command Injection** | Không dùng shell commands với user input |
| **Template Injection** | Auto-escaping, không dùng dynamic templates |

---

## 11. Thư Viện & Thuật Toán Bảo Mật

### 11.1 Thư Viện Python/Django

| Thư Viện | Version | Mục Đích |
|----------|---------|----------|
| `django` | 5.x | Web framework với built-in security |
| `django-axes` | 8.0.0 | Brute-force protection |
| `django-allauth` | Latest | Authentication với rate limiting |
| `django-csp` | 4.0+ | Content Security Policy |
| `cryptography` | Latest | Cryptographic primitives |
| `argon2-cffi` | Latest | Argon2 password hashing |
| `django-redis` | Latest | Cache backend (production) |

### 11.2 Thuật Toán Cryptographic

| Thuật Toán | Use Case | Specification |
|------------|----------|---------------|
| **Argon2id** | Password hashing | RFC 9106, PHC winner |
| **AES-128-CBC** | Field encryption (Fernet) | FIPS 197 |
| **HMAC-SHA256** | Message authentication | RFC 2104 + FIPS 180-4 |
| **SHA-256** | General hashing | FIPS 180-4 |
| **RSA** | Backup signatures | PKCS#1 |
| **scrypt** | Backup password hashing | RFC 7914 |
| **PBKDF2-HMAC-SHA256** | Legacy compatibility | RFC 8018 |

### 11.3 Algorithm Parameters

#### Argon2id Parameters

```python
# Django's default Argon2 settings
ARGON2_TIME_COST = 2           # Number of iterations
ARGON2_MEMORY_COST = 102400    # 100 MB
ARGON2_PARALLELISM = 8         # Threads
ARGON2_HASH_LENGTH = 32        # 256 bits
ARGON2_SALT_LENGTH = 16        # 128 bits
```

#### HMAC-SHA256

```
Key length: 256+ bits (SECRET_KEY)
Output length: 256 bits (64 hex chars)
Security level: 128-bit collision resistance
```

### 11.4 TLS Configuration

| Setting | Value |
|---------|-------|
| Protocol | TLS 1.2+ |
| Cipher Suites | Modern (AEAD preferred) |
| Certificate | Let's Encrypt / Commercial CA |
| HSTS | 1 year, includeSubDomains, preload |

---

## 12. Tổng Kết & Khuyến Nghị

### 12.1 Security Controls Summary

| Layer | Control | Status |
|-------|---------|--------|
| 1 | HTTPS/HSTS | ✅ Implemented |
| 2 | CSP + Security Headers | ✅ Implemented |
| 3 | Rate Limiting + AXES | ✅ Implemented |
| 4 | Argon2 + Session Security | ✅ Implemented |
| 5 | Database Isolation | ✅ Implemented |
| 6 | RBAC + Site Authorization | ✅ Implemented |
| 7 | Field Encryption | ✅ Implemented |
| 8 | Audit Logging + Checksums | ✅ Implemented |

### 12.2 Compliance Alignment

| Standard | Relevant Controls |
|----------|-------------------|
| **OWASP Top 10** | All 10 risks addressed |
| **HIPAA** | Audit logging, encryption, access control |
| **GDPR** | Audit trail, encryption, access control |
| **21 CFR Part 11** | Audit trail, electronic signatures |

### 12.3 Khuyến Nghị Cải Thiện

#### Mức Độ Ưu Tiên Cao

1. **Two-Factor Authentication (2FA)**
   - Thêm TOTP (Google Authenticator)
   - SMS backup codes

2. **IP Allowlist cho Admin**
   - Giới hạn truy cập `/admin/` từ specific IPs

3. **Automated Security Scanning**
   - SAST: Bandit, Safety
   - DAST: OWASP ZAP

#### Mức Độ Ưu Tiên Trung Bình

4. **Database Query Logging**
   - Log sensitive queries (DELETE, UPDATE on PII)

5. **Data Masking**
   - Mask PII trong non-production environments

6. **Key Rotation Automation**
   - Scheduled rotation cho FERNET_KEYS

#### Mức Độ Ưu Tiên Thấp

7. **Bug Bounty Program**
   - Mời security researchers tìm lỗ hổng

8. **Penetration Testing**
   - Annual pentest bởi third-party

---

## Appendix A: Security Headers Response

```http
HTTP/1.1 200 OK
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-abc123' https://cdn.jsdelivr.net; frame-ancestors 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Cache-Control: no-cache, no-store, must-revalidate, private
```

## Appendix B: Password Hash Format

```
Argon2 hash format:
$argon2id$v=19$m=102400,t=2,p=8$<salt>$<hash>

Example:
$argon2id$v=19$m=102400,t=2,p=8$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG
```

## Appendix C: Audit Log Checksum Format

```
HMAC-SHA256 output: 64 hexadecimal characters
Example: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

---

**Document Version:** 1.0  
**Last Updated:** 15/01/2026  
**Author:** Security Architecture Review  
**Classification:** Internal Use Only
