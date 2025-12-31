# 📋 Hướng dẫn: Hiển thị Axes Lockout Error trong Login Form

**Ngày tạo:** 31/12/2025  
**Yêu cầu:** Thay vì redirect sang `lockout.html`, hiển thị error message ngay trong `login.html`

---

## 🎯 Mục tiêu

| Hiện tại | Mong muốn |
|----------|-----------|
| User bị lock → Redirect đến `/errors/lockout.html` | User bị lock → Hiển thị error message trong login form |
| Trang lockout riêng biệt | Trải nghiệm liền mạch, không chuyển trang |

---

## 📊 Phân tích Cơ chế Hiện tại

### Cách Django-Axes xử lý Lockout:

```
User login sai 7 lần
        ↓
AxesMiddleware intercept request
        ↓
Check is_locked() → True
        ↓
Return lockout response (AXES_LOCKOUT_TEMPLATE hoặc AXES_LOCKOUT_CALLABLE)
        ↓
Render lockout.html (REDIRECT)
```

### Cấu hình hiện tại (`base.py`):
```python
AXES_LOCKOUT_TEMPLATE = "errors/lockout.html"  # Redirect đến template này
```

---

## 🛠️ Các Phương án Giải quyết

### **Phương án A: Sử dụng `AXES_LOCKOUT_CALLABLE` (Khuyến nghị ⭐)**

Tạo custom lockout handler trả về login page với error message.

**Ưu điểm:**
- Không cần sửa allauth views
- Giữ nguyên flow hiện tại
- Dễ maintain

**Nhược điểm:**
- Cần tạo thêm function handler

---

### **Phương án B: Custom Allauth LoginView với `axes_dispatch` decorator**

Override Allauth LoginView để catch axes exception và hiển thị error.

**Ưu điểm:**
- Kiểm soát hoàn toàn flow
- Có thể thêm logic phức tạp

**Nhược điểm:**
- Phức tạp hơn
- Cần maintain custom view

---

### **Phương án C: Signal Handler (Đơn giản nhất)**

Catch `user_locked_out` signal và store message trong session.

**Ưu điểm:**
- Đơn giản nhất
- Không cần thay đổi nhiều

**Nhược điểm:**
- Vẫn có thể redirect trước khi signal chạy

---

## ✅ Phương án Khuyến nghị: Kết hợp A + Custom Form

### Bước 1: Tạo Custom Lockout Handler

**File mới:** `backends/api/base/account/lockout.py`

```python
# backends/api/base/account/lockout.py
"""
Custom lockout handler for django-axes.
Returns login page with error message instead of redirect.
"""
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


def lockout_response(request, credentials, *args, **kwargs):
    """
    Custom lockout handler that renders login page with error message.
    
    Args:
        request: HttpRequest object
        credentials: Dict with username/email
        *args, **kwargs: Additional arguments from axes
        
    Returns:
        HttpResponse: Login page with lockout error message
    """
    from allauth.account.forms import LoginForm
    
    # Get username from credentials
    username = credentials.get('username') or credentials.get('login', 'Unknown')
    
    # Create form with initial data
    form = LoginForm(initial={'login': username})
    
    # Add lockout error to form
    lockout_message = _(
        "Your account has been temporarily locked due to multiple failed login attempts. "
        "Please try again in 30 minutes or contact support for assistance."
    )
    form.add_error(None, lockout_message)
    
    context = {
        'form': form,
        'is_locked_out': True,  # Flag for template
        'lockout_username': username,
    }
    
    return render(
        request, 
        'account/login.html', 
        context,
        status=403  # Forbidden status
    )
```

### Bước 2: Cập nhật Settings

**File:** `config/settings/base.py`

```python
# Thay thế AXES_LOCKOUT_TEMPLATE bằng AXES_LOCKOUT_CALLABLE
# AXES_LOCKOUT_TEMPLATE = "errors/lockout.html"  # Xóa hoặc comment

AXES_LOCKOUT_CALLABLE = "backends.api.base.account.lockout.lockout_response"
```

### Bước 3: Cập nhật Login Template

**File:** `frontends/templates/account/login.html`

Thêm xử lý cho `is_locked_out` context:

```html
<!-- Error Messages - Enhanced for Lockout -->
{% if is_locked_out %}
<div class="alert alert-danger d-flex align-items-start px-3 py-3" role="alert" aria-live="assertive">
    <i class="bi bi-shield-lock-fill me-3 fs-4" aria-hidden="true"></i>
    <div>
        <strong>{% trans "Account Locked" %}</strong>
        <p class="small mb-0 mt-1">
            {% trans "Your account has been temporarily locked due to multiple failed login attempts." %}
            {% trans "Please try again in 30 minutes or contact support." %}
        </p>
    </div>
</div>
{% elif form.errors %}
<div class="alert alert-danger d-flex align-items-center px-3 py-2" role="alert" aria-live="polite">
    <i class="bi bi-exclamation-triangle-fill me-3" aria-hidden="true"></i>
    <div class="small">
        {% for error in form.non_field_errors %}
        {{ error }}
        {% endfor %}
    </div>
</div>
{% endif %}
```

### Bước 4: (Tùy chọn) Disable form khi locked

Thêm vào template để disable form khi bị lock:

```html
<!-- Login Form -->
<form method="POST" action="{% url 'account_login' %}" id="loginForm" class="auth-form">
    {% csrf_token %}
    
    <fieldset {% if is_locked_out %}disabled{% endif %}>
        <!-- Username/Email Input -->
        <div class="mb-4">
            <!-- ... existing code ... -->
        </div>
        
        <!-- Password Input -->
        <div class="mb-4">
            <!-- ... existing code ... -->
        </div>
        
        <!-- Submit Button -->
        <button type="submit" class="btn btn-cyber w-100" id="submitBtn" 
                {% if is_locked_out %}disabled{% endif %}>
            <!-- ... existing code ... -->
        </button>
    </fieldset>
</form>

{% if is_locked_out %}
<!-- Countdown timer (optional) -->
<div class="text-center mt-3">
    <small class="text-muted">
        <i class="bi bi-clock me-1"></i>
        {% trans "Try again in" %}: <span id="countdown">30:00</span>
    </small>
</div>
{% endif %}
```

---

## 📁 Cấu trúc File sau khi Implement

```
backends/
└── api/
    └── base/
        └── account/
            ├── __init__.py
            ├── adapter.py          # Existing
            └── lockout.py          # NEW - Custom lockout handler

config/
└── settings/
    └── base.py                     # Modified - AXES_LOCKOUT_CALLABLE

frontends/
└── templates/
    └── account/
        └── login.html              # Modified - Add lockout error display
```

---

## 🔄 Flow sau khi Implement

```
User login sai 7 lần
        ↓
AxesMiddleware intercept request
        ↓
Check is_locked() → True
        ↓
Call AXES_LOCKOUT_CALLABLE (lockout_response)
        ↓
Render login.html với:
  - form.errors chứa lockout message
  - is_locked_out = True
  - status = 403
        ↓
User thấy login form + error message (KHÔNG REDIRECT)
```

---

## ⚠️ Lưu ý Quan trọng

### 1. Cần thiết lập Axes-Allauth Integration

Để axes hoạt động đúng với allauth, cần thêm cấu hình:

```python
# settings.py
AXES_USERNAME_FORM_FIELD = 'login'  # Allauth sử dụng 'login' thay vì 'username'
```

### 2. Custom LoginForm cho Axes

Nếu muốn tracking chính xác hơn, tạo custom form:

```python
# backends/api/base/account/forms.py
from allauth.account.forms import LoginForm

class AxesLoginForm(LoginForm):
    """Extended login form for Axes compatibility."""
    
    def user_credentials(self):
        credentials = super().user_credentials()
        # Đảm bảo 'login' key tồn tại cho axes
        credentials['login'] = credentials.get('email') or credentials.get('username')
        return credentials
```

### 3. Decorate LoginView (Tùy chọn - để tracking tốt hơn)

```python
# config/urls/base.py hoặc một file urls tùy chỉnh
from django.utils.decorators import method_decorator
from allauth.account.views import LoginView
from axes.decorators import axes_dispatch, axes_form_invalid

# Decorate methods
LoginView.dispatch = method_decorator(axes_dispatch)(LoginView.dispatch)
LoginView.form_invalid = method_decorator(axes_form_invalid)(LoginView.form_invalid)
```

---

## 🧪 Test Cases

| Test Case | Expected Result |
|-----------|-----------------|
| Login sai 1-6 lần | Hiển thị "Invalid credentials" error |
| Login sai lần thứ 7 | Hiển thị "Account Locked" message + form disabled |
| Đợi 30 phút, login lại | Cho phép login bình thường |
| Login đúng sau khi hết cooloff | Reset counter, login thành công |
| Admin reset axes | User có thể login ngay |

---

## 📝 Checklist Implementation

- [ ] Tạo file `backends/api/base/account/lockout.py`
- [ ] Cập nhật `AXES_LOCKOUT_CALLABLE` trong `base.py`
- [ ] Xóa/comment `AXES_LOCKOUT_TEMPLATE`
- [ ] Thêm `AXES_USERNAME_FORM_FIELD = 'login'` (nếu chưa có)
- [ ] Cập nhật `login.html` với lockout error display
- [ ] (Tùy chọn) Tạo `AxesLoginForm` 
- [ ] (Tùy chọn) Decorate `LoginView`
- [ ] Test toàn bộ flow
- [ ] Xóa file `lockout.html` (nếu không cần nữa)

---

## 🎨 UI Mockup

### Trước (Redirect):
```
[Login Page] → Submit sai 7 lần → [Lockout Page]
     ↓                                    ↓
 Trang riêng                      Trang thông báo bị khóa
```

### Sau (Inline Error):
```
[Login Page] → Submit sai 7 lần → [Login Page + Error]
     ↓                                    ↓
 Form login                       Form login + Alert "Account Locked"
                                  + Form disabled
                                  + Countdown timer (optional)
```

---

**Báo cáo bởi:** GitHub Copilot  
**Yêu cầu thêm:** Hãy cho tôi biết nếu bạn muốn implement bất kỳ phương án nào!
