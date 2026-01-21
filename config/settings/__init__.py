"""
Settings router - automatically loads dev or prod settings based on environment.

Environment detection via DJANGO_ENV:
- "prod" or "production" → prod.py
- "test"                  → dev.py with test-specific overrides
- "dev" or other          → dev.py (default)

Usage:
    export DJANGO_ENV=prod  # Linux/Mac
    set DJANGO_ENV=prod     # Windows

    python manage.py runserver              # Uses dev settings
    DJANGO_ENV=prod gunicorn config.wsgi    # Uses prod settings
"""
import os

DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev").lower()

if DJANGO_ENV in ("prod", "production"):
    from .prod import *  # noqa: F401, F403
elif DJANGO_ENV == "test":
    from .dev import *  # noqa: F401, F403

    # Test-specific overrides
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    # Default to development
    from .dev import *  # noqa: F401, F403