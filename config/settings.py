import os
from pathlib import Path
from dotenv import load_dotenv

# === Paths & .env ===
BASE_DIR = Path(__file__).resolve().parent.parent  # -> ResSync/
load_dotenv(BASE_DIR / ".env")  # Load .env từ project root

# === Core settings ===
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-default-key")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

CSRF_TRUSTED_ORIGINS = (
    os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if os.getenv("CSRF_TRUSTED_ORIGINS")
    else []
)

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# === Installed apps ===
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "django_bootstrap5",
    "chartjs",

    # ResSync apps
    "apps.web",
    "apps.tenancy.apps.TenancyConfig"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # Tenancy (lazy-load dynamic DB + set_current_db theo study)
    "apps.tenancy.middleware.StudyRoutingMiddleware",
]

# === Templates ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "web" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

# ---- Database: DB quản lý (db_management) luôn có sẵn ----
_DB_MANAGEMENT = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("PGDATABASE", "db_management"),
    "USER": os.getenv("PGUSER", "resync_app"),
    "PASSWORD": os.getenv("PGPASSWORD", ""),
    "HOST": os.getenv("PGHOST", "localhost"),
    "PORT": os.getenv("PGPORT", "5432"),
    "OPTIONS": {"options": "-c search_path=auth,metadata,public"},
    "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
    # Devtest: để False cho nhẹ; db_loader sẽ copy giá trị này sang DB động để khỏi lỗi KeyError
    "ATOMIC_REQUESTS": False,
    "AUTOCOMMIT": True,
    "CONN_MAX_AGE": int(os.getenv("PG_CONN_MAX_AGE", "600")),
    # (tuỳ chọn) Health checks
    "CONN_HEALTH_CHECKS": False,
    # (tuỳ chọn) Khi bạn chạy server ở VN, giữ TZ đồng nhất
    "TIME_ZONE": os.getenv("DB_TIME_ZONE", "Asia/Ho_Chi_Minh"),
}

DATABASES = {
    "default": _DB_MANAGEMENT,       # cho tiện, default = db_management
    "db_management": _DB_MANAGEMENT, # alias rõ ràng cho router/middleware
}

# ---- Template cho DB nghiên cứu (mọi study active sẽ clone cấu hình này) ----
STUDY_DB_AUTO_REFRESH_SECONDS = int(os.getenv("STUDY_DB_AUTO_REFRESH_SECONDS", "300"))

# Prefix tên DB nghiên cứu (bảo vệ & đối chiếu)
STUDY_DB_PREFIX = os.getenv("STUDY_DB_PREFIX", "db_study_")
STUDY_DB_ENGINE = "django.db.backends.postgresql"
STUDY_DB_HOST = os.getenv("STUDY_PGHOST", _DB_MANAGEMENT["HOST"])
STUDY_DB_PORT = os.getenv("STUDY_PGPORT", _DB_MANAGEMENT["PORT"])
STUDY_DB_USER = os.getenv("STUDY_PGUSER", _DB_MANAGEMENT["USER"])
STUDY_DB_PASSWORD = os.getenv("STUDY_PGPASSWORD", _DB_MANAGEMENT["PASSWORD"])
STUDY_DB_SEARCH_PATH = os.getenv("STUDY_SEARCH_PATH", "public")  # có thể để public

# Router
DATABASE_ROUTERS = ["apps.tenancy.db_router.StudyDBRouter"]
MIDDLEWARE.insert(0, "apps.tenancy.middleware.StudyRoutingMiddleware")

# === i18n & timezone ===
LANGUAGE_CODE = "vi"
LANGUAGES = [("vi", "Vietnamese"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_L10N = True
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_TZ = True

# === Static & media ===
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "web" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# MEDIA_URL = "/media/"
# MEDIA_ROOT = BASE_DIR / "media"

# === Authentication ===
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

FEATURE_PASSWORD_RESET = False # Tắt tính năng reset mật khẩu (chưa làm xong)
# # === Email (devtest: in ra console) ===
# EMAIL_BACKEND = os.getenv(
#     "EMAIL_BACKEND",
#     "django.core.mail.backends.console.EmailBackend"  # mặc định in ra console khi thiếu cấu hình
# )
# EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
# EMAIL_HOST = os.getenv("EMAIL_HOST", "")
# EMAIL_PORT = int(os.getenv("EMAIL_PORT", "0") or 0)
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
# EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
# EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false").lower() in ("1","true","yes","on")
# EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() in ("1","true","yes","on")
# EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))

# DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", f"ResSync <no-reply@hcmus.org>")
# SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
# PASSWORD_RESET_TIMEOUT = int(os.getenv("PASSWORD_RESET_TIMEOUT", "600"))

# === Security (devtest: để False) ===
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("1","true","yes")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() in ("1","true","yes")
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))

# === Defaults ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === Logging (console + file) ===
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[%(levelname)s] %(message)s"},
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": str(LOGS_DIR / "django.log"),
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
}

# === Custom settings ===
TENANCY_ENABLED = os.getenv("TENANCY_ENABLED", "False").lower() in ("true", "1", "yes")
TENANCY_STUDY_CODE_PREFIX = os.getenv("TENANCY_STUDY_CODE_PREFIX", "study_")    