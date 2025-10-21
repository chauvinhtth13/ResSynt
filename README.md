# ResSync - Research Data Management Platform

## 🎯 Giới thiệu

**ResSync** là nền tảng quản lý và trực quan hóa dữ liệu nghiên cứu an toàn, được thiết kế để tối ưu hóa các dự án học thuật và khoa học. Hệ thống tập trung hóa việc xử lý dữ liệu từ thu thập đến phân tích, cung cấp dashboard trực quan cho insights thời gian thực, trực quan hóa xu hướng và ra quyết định dựa trên dữ liệu.

## 🏗️ Kiến trúc Hệ thống

### 1. Tổng quan Architecture

ResSync được xây dựng theo kiến trúc **Multi-Tenant Database** với Django framework:

```
┌─────────────────────────────────────────────────────────────┐
│                      ResSync Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐      ┌──────────────┐     ┌─────────────┐ │
│  │  Frontend   │◄────►│   Backend    │◄───►│  Database   │ │
│  │  (HTML/JS)  │      │   (Django)   │     │ (PostgreSQL)│ │
│  └─────────────┘      └──────────────┘     └─────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Cấu trúc Thư mục

```
ResSync/
├── backends/                    # Backend Logic
│   ├── api/                    # API Endpoints
│   │   ├── base/              # Authentication & Core APIs
│   │   └── studies/           # Study-specific APIs
│   │       └── study_43en/    # Example: Study 43EN
│   ├── studies/               # Study Applications
│   │   └── study_43en/       # Models, Forms, Utils
│   │       ├── models/       # Data Models
│   │       ├── utils/        # Utilities & Helpers
│   │       └── migrations/   # Database Migrations
│   └── tenancy/              # Multi-Tenancy Management
│       ├── models/           # User, Study, Site Models
│       ├── middleware.py     # Request Routing & Security
│       ├── db_loader.py      # Dynamic DB Management
│       └── utils/            # Role & Permission Management
├── frontends/                 # Frontend Assets
│   ├── templates/            # HTML Templates
│   └── static/               # CSS, JavaScript, Images
│       ├── css/
│       ├── js/
│       │   ├── default/      # Core JavaScript
│       │   └── studies/      # Study-specific JS
│       └── images/
├── config/                    # Django Configuration
│   ├── settings.py           # Main Settings
│   ├── urls.py               # URL Routing
│   ├── wsgi.py               # WSGI Config
│   └── asgi.py               # ASGI Config
├── script/                    # Utility Scripts
├── manage.py                  # Django Management
└── requirements.txt           # Python Dependencies
```

## 🔧 Các Thành phần Chính

### 1. **Multi-Tenancy System**

#### Database Architecture
- **Management Database (`default`)**: Quản lý users, studies, sites
- **Study Databases (`db_study_*`)**: Mỗi nghiên cứu có database riêng biệt
- **Database Isolation**: Tách biệt hoàn toàn giữa các nghiên cứu

```python
# Tự động tạo database cho mỗi study
db_name = f"db_study_{study_code.lower()}"

# Schema structure trong mỗi study database
Schemas:
  - data          # Dữ liệu nghiên cứu chính
  - audit_log     # Nhật ký kiểm toán
```

#### Database Router
```python
# backends/tenancy/db_router.py
- Tự động routing queries đến đúng database
- Thread-safe context management
- Dynamic database switching
```

### 2. **Authentication & Authorization**

#### User Management
```python
# backends/tenancy/models/user.py
- Extended AbstractUser
- Integration với Django Axes (brute-force protection)
- Password policy enforcement
- Failed login tracking
```

#### Role-Based Access Control (RBAC)
```python
Roles Hierarchy:
1. Principal Investigator (PI) - Quyền cao nhất
2. Data Manager - Quản lý dữ liệu
3. Site Coordinator - Điều phối site
4. Data Entry Clerk - Nhập liệu
5. Monitor - Giám sát
6. Read Only - Chỉ xem
```

### 3. **Middleware Pipeline**

```python
# backends/tenancy/middleware.py - UnifiedTenancyMiddleware

Request Flow:
1. Security Headers Addition
2. Static File Fast Path
3. Authentication Check
4. Study Context Detection
5. Database Switching
6. Permission Validation
7. Performance Monitoring
8. Response Enhancement
```

**Middleware Features:**
- ✅ Path matching với compiled regex (hiệu suất cao)
- ✅ Study context auto-detection từ URL
- ✅ Dynamic database routing
- ✅ Security headers injection
- ✅ Performance metrics tracking
- ✅ Cache control management
- ✅ Connection cleanup

### 4. **Audit Logging System**

#### Backend Audit System
```python
# backends/studies/study_43en/models/audit_log.py

AuditLog Model:
- User tracking (user_id, username)
- Action types (CREATE, UPDATE, DELETE, VIEW)
- Data versioning (old_data, new_data)
- Reason tracking (reason, reasons_json)
- Site filtering (SITEID)
- IP address logging
```

#### Frontend Audit Integration
```javascript
// frontends/static/js/studies/study_43en/audit-log/

Audit Modules:
- clinical-form.js        # Clinical data auditing
- microbiology-form.js    # Lab data auditing
- laboratory-log.js       # Laboratory auditing
- antibio-form.js         # Antibiotic sensitivity
- endcasecrf-form.js      # End case auditing
```

**Audit Flow:**
1. Capture initial form values
2. Track user changes
3. Prompt for change reasons
4. Store old/new data comparison
5. Log to database với metadata

### 5. **Data Management**

#### Models Structure
```python
# backends/studies/study_43en/models/

Key Models:
- ScreeningCase      # Sàng lọc bệnh nhân
- EnrollmentCase     # Đăng ký nghiên cứu
- ClinicalCase       # Dữ liệu lâm sàng
- MicrobiologyCase   # Vi sinh
- LaboratoryCase     # Xét nghiệm
- AntibioticData     # Kháng sinh
- FollowUpStatus     # Theo dõi
```

#### Form Management
```python
- Django Forms với validation
- Formsets cho data phức tạp
- Custom validators
- Auto-save functionality
```
