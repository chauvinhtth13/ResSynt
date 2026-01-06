"""
Settings router - automatically loads dev or prod settings based on environment.
"""
import os

DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev").lower()

if DJANGO_ENV == "prod":
    from .prod import *
elif DJANGO_ENV == "test":
    from .dev import *
    # Test uses same PostgreSQL as dev, override specific settings if needed
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    from .dev import *