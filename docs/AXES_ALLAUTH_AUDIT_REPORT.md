# 📋 Django-Axes & Django-Allauth Audit Report

**Ngày tạo:** 31/12/2025  
**Dự án:** ResSynt - Research Data Management Platform  
**Phiên bản:** django-axes 8.0.0, django-allauth (latest)

---

## 🔴 CÁC VẤN ĐỀ NGHIÊM TRỌNG (CRITICAL)

### 1. ❌ AUTHENTICATION_BACKENDS - THỨ TỰ SAI

**File:** `config/settings/base.py` (Line 162-166)

```python
# HIỆN TẠI (SAI)
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend", 
    "axes.backends.AxesBackend",  # Must be last  ← COMMENT SAI!
]
```

**Vấn đề:**
- `AxesBackend` **PHẢI Ở ĐẦU TIÊN**, không phải cuối cùng
- Khi ở cuối, axes không thể intercept authentication để track failed attempts
- Đây là **nguyên nhân chính** axes không hoạt động

**Giải pháp:**
```python
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",  # MUST BE FIRST - intercepts all auth attempts
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
```

---

### 2. ❌ AXES_COOLOFF_TIME = None (Không có thời gian mở khóa)

**File:** `config/settings/base.py` (Line 201)

```python
AXES_COOLOFF_TIME = None  # Hiện tại
```

**Vấn đề:**
- Khi `None`, user bị khóa **vĩnh viễn** cho đến khi admin reset
- Không có cơ chế tự động mở khóa
- Có thể gây DoS nếu attacker biết username

**Giải pháp:**
```python
from datetime import timedelta
AXES_COOLOFF_TIME = timedelta(minutes=30)  # Auto-unlock sau 30 phút
```

---

### 3. ❌ FILE tasks.py KHÔNG TỒN TẠI (Import Error)

**File:** `backends/tenancy/signals.py` (Line 157)

```python
from backends.tenancy.tasks import send_security_alert  # FILE KHÔNG TỒN TẠI!
```

**Vấn đề:**
- Signal `handle_axes_lockout` sẽ crash với `ImportError`
- Không thể gửi email alert khi user bị lockout
- Celery task không được định nghĩa

**Giải pháp:** Tạo file `backends/tenancy/tasks.py`:
```python
# backends/tenancy/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_security_alert(self, alert_type: str, details: dict):
    """Send security alert email asynchronously"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"[Security Alert] {alert_type}"
        message = f"Security Event: {alert_type}\nDetails: {details}"
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        logger.info(f"Security alert sent: {alert_type}")
        
    except Exception as e:
        logger.error(f"Failed to send security alert: {e}")
        raise self.retry(exc=e, countdown=60)
```

---

## 🟠 VẤN ĐỀ TRUNG BÌNH (MEDIUM)

### 4. ⚠️ Signal Signature Có Thể Không Tương Thích

**File:** `backends/tenancy/signals.py` (Line 136)

```python
# Axes 8.0.0 có thể có signature khác nhau tùy version
@receiver(user_locked_out)
def handle_axes_lockout(request, credentials, **kwargs):
```

**Kiểm tra:**
- Verify axes version: `pip show django-axes`
- Kiểm tra documentation cho signature chính xác

---

### 5. ⚠️ AXES_LOCKOUT_PARAMETERS Kết Hợp Có Thể Gây Vấn Đề

**File:** `config/settings/base.py` (Line 202)

```python
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
```

**Vấn đề tiềm ẩn:**
- Track theo cả username VÀ IP
- Nếu user đổi IP, có thể bypass lockout
- Nếu nhiều user dùng chung IP (VPN/office), có thể bị lock nhầm

**Khuyến nghị:** Chọn một trong hai:
```python
# Option A: Chỉ theo username (an toàn hơn)
AXES_LOCKOUT_PARAMETERS = ["username"]

# Option B: Kết hợp nhưng dùng combination key
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]  # Both required
```

---

### 6. ⚠️ is_axes_locked() Method Phức Tạp Không Cần Thiết

**File:** `backends/tenancy/models/user.py` (Line 209-257)

**Vấn đề:**
- Tạo MockRequest phức tạp
- Có thể không hoạt động đúng với mọi axes config

**Giải pháp đơn giản hơn:**
```python
def is_axes_locked(self) -> bool:
    """Check if user is locked by django-axes"""
    try:
        from axes.models import AccessAttempt
        from django.conf import settings
        
        attempt = AccessAttempt.objects.filter(
            username=self.username
        ).order_by('-attempt_time').first()
        
        if not attempt:
            return False
        
        # Check if within cooloff period
        cooloff = getattr(settings, 'AXES_COOLOFF_TIME', None)
        if cooloff:
            from django.utils import timezone
            if attempt.attempt_time + cooloff < timezone.now():
                return False  # Cooloff expired
        
        failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        return attempt.failures_since_start >= failure_limit
        
    except Exception as e:
        logger.error(f"Error checking axes lock: {e}")
        return False
```

---

## 🟡 VẤN ĐỀ NHẸ (LOW)

### 7. ℹ️ Allauth Adapter Thiếu Chức Năng

**File:** `backends/api/base/account/adapter.py`

```python
class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False
    
    def get_from_email(self):
        return 'ResSync- Research Data Management Platform'  # Typo: "ResSync" vs "ResSynt"
```

**Khuyến nghị thêm:**
```python
class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False
    
    def get_from_email(self):
        return 'ResSynt - Research Data Management Platform'
    
    def get_login_redirect_url(self, request):
        """Redirect based on user role after login"""
        if request.user.is_superuser:
            return '/admin/'
        return '/select-study/'
    
    def login(self, request, user):
        """Hook to track login via allauth"""
        super().login(request, user)
        # Additional logging/tracking if needed
```

---

### 8. ℹ️ ACCOUNT_RATE_LIMITS Trùng Lặp Với Axes

**File:** `config/settings/base.py` (Line 181-188)

```python
ACCOUNT_RATE_LIMITS = {
    "login": "5/m/ip",
    "login_failure": "5/m/ip",  # Trùng với AXES_FAILURE_LIMIT
    ...
}
```

**Vấn đề:**
- Allauth rate limit (5/phút) xung đột với Axes limit (7 attempts)
- Có thể gây nhầm lẫn về behavior

**Khuyến nghị:**
```python
# Disable allauth rate limits cho login, để axes handle
ACCOUNT_RATE_LIMITS = {
    "change_password": "5/m/user",
    "reset_password": "10/m/ip",
    "reset_password_email": "5/m/ip",
    "reset_password_from_key": "20/m/ip",
    # Remove login rate limits - let axes handle
}
```

---

### 9. ℹ️ Lockout Template Có Comment Sai

**File:** `frontends/templates/errors/lockout.html` (Line 1)

```html
<!-- frontends\templates\authentication\login.html -->  ← COMMENT SAI!
```

**Nên sửa:**
```html
<!-- frontends/templates/errors/lockout.html -->
```

---

## ✅ CHECKLIST SỬA LỖI

| # | Mức độ | Vấn đề | File | Status |
|---|--------|--------|------|--------|
| 1 | 🔴 Critical | AxesBackend order | base.py | ⬜ |
| 2 | 🔴 Critical | AXES_COOLOFF_TIME | base.py | ⬜ |
| 3 | 🔴 Critical | tasks.py missing | tenancy/ | ⬜ |
| 4 | 🟠 Medium | Signal signature | signals.py | ⬜ |
| 5 | 🟠 Medium | LOCKOUT_PARAMETERS | base.py | ⬜ |
| 6 | 🟠 Medium | is_axes_locked() | user.py | ⬜ |
| 7 | 🟡 Low | Adapter functions | adapter.py | ⬜ |
| 8 | 🟡 Low | Rate limits overlap | base.py | ⬜ |
| 9 | 🟡 Low | Template comment | lockout.html | ⬜ |

---

## 🔧 LỆNH KIỂM TRA

```bash
# 1. Check axes version
pip show django-axes

# 2. Check if axes tables exist
python manage.py showmigrations axes

# 3. Run migrations if needed
python manage.py migrate axes

# 4. Check axes in Django check
python manage.py check

# 5. Test axes manually
python manage.py shell
>>> from axes.models import AccessAttempt, AccessLog
>>> AccessAttempt.objects.all()
>>> AccessLog.objects.all()

# 6. Reset all axes locks
python manage.py axes_reset

# 7. Reset specific user
python manage.py axes_reset_user username
```

---

## 📊 CẤU HÌNH KHUYẾN NGHỊ CUỐI CÙNG

```python
# config/settings/base.py

# AUTHENTICATION - CORRECT ORDER
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",  # MUST BE FIRST
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# AXES - OPTIMIZED
from datetime import timedelta

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 7
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_PARAMETERS = ["username"]  # Simpler, more secure
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_AT_FAILURE = True
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_VERBOSE = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_LOCKOUT_TEMPLATE = "errors/lockout.html"
AXES_IPWARE_PROXY_COUNT = 1
AXES_IPWARE_META_PRECEDENCE_ORDER = [
    "HTTP_X_FORWARDED_FOR",
    "X_FORWARDED_FOR", 
    "REMOTE_ADDR",
]

# ALLAUTH - Disable login rate limits (let axes handle)
ACCOUNT_RATE_LIMITS = {
    "change_password": "5/m/user",
    "reset_password": "10/m/ip",
    "reset_password_email": "5/m/ip",
    "reset_password_from_key": "20/m/ip",
    # Login handled by axes
}
```

---

## 🧪 TEST PLAN

1. **Test Failed Login Tracking:**
   - Login sai 3 lần với cùng user
   - Kiểm tra `axes_accessattempt` table có record
   - Kiểm tra log có warning messages

2. **Test Lockout:**
   - Login sai 7 lần
   - Verify redirect đến lockout.html
   - Verify không thể login dù đúng password

3. **Test Cooloff:**
   - Sau khi bị lock, đợi 30 phút
   - Verify có thể login lại

4. **Test Reset on Success:**
   - Login sai 3 lần
   - Login đúng
   - Verify counter reset về 0

5. **Test Allauth Integration:**
   - Login qua allauth
   - Verify axes signal được trigger
   - Check log messages

---

**Báo cáo tạo bởi:** GitHub Copilot  
**Cần hỗ trợ thêm:** Liên hệ để implement các fix
