import os
from pathlib import Path
from dotenv import load_dotenv

# === Paths & .env ===
BASE_DIR = Path(__file__).resolve().parent.parent  # two levels up -> project root (ResSync/)
load_dotenv(BASE_DIR / ".env")  # .env at project root

# === Core ===
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-default-key")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# For production deployment (add this block)
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []

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
    "apps.tenancy.apps.TenancyConfig",
    "apps.study_templates",
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
]

# === Templates ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "web" / "templates"],  # <- dùng template của bạn
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

# === Database (đọc từ .env + set search_path) ===
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("PGDATABASE", "db_management"),
        "USER": os.getenv("PGUSER", "app_user"),
        "PASSWORD": os.getenv("PGPASSWORD", ""),
        "HOST": os.getenv("PGHOST", "localhost"),
        "PORT": os.getenv("PGPORT", "5432"),
        "OPTIONS": {
            "options": "-c search_path=studies_management,public"
        },
    }
}

# === i18n ===
LANGUAGE_CODE = "vi"
LANGUAGES = [("vi", "Vietnamese"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_L10N = True
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_TZ = True

# === Static & Media ===
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "web" / "static"]  # source for dev
STATIC_ROOT = BASE_DIR / "staticfiles"                     # collectstatic target for prod


# # Optional media (enable if/when you need uploads)
# MEDIA_URL = "/media/"
# MEDIA_ROOT = BASE_DIR / "media"

# === Authentication ===
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"          # sau khi đăng nhập xong đi đâu
LOGOUT_REDIRECT_URL = "/accounts/login/"  # sau khi logout

# === Django defaults ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === Logging (simple, expand in prod as needed) ===
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not DEBUG else "DEBUG",
    },
}
