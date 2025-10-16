#!/usr/bin/env python
# manage.py
import os
import sys
from pathlib import Path

def main():
    ROOT = Path(__file__).resolve().parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))  # Ensures root is first in path for imports like 'config.settings'

    try:
        import environ
        environ.Env.read_env(ROOT / ".env")  # Load .env into os.environ
    except ImportError:
        print("Warning: 'django-environ' not installed; skipping .env load. Install it for better env management.")
    except Exception as e:
        print(f"Error loading .env: {e}")  # Basic error feedback

    # Set default settings module; can override via env var
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"))

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH? "
            "Did you forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()