import os
from pathlib import Path
from dotenv import load_dotenv

# === Paths & .env ===
BASE_DIR = Path(__file__).resolve().parent.parent  # <- sửa: chỉ 2 cấp
load_dotenv(BASE_DIR / ".env")                     # .env ở gốc dự án

# === Core ===
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-default-key")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# === Installed apps ===
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_bootstrap5",
    "chartjs",

    # apps của bạn:
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

# === Static files ===
STATIC_URL = "/static/"  # <- URL
STATICFILES_DIRS = [BASE_DIR / "apps" / "web" / "static"]  # <- nguồn static
# (prod) nơi collectstatic gom vào:
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
