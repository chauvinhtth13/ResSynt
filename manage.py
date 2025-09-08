#!/usr/bin/env python
# manage.py
import os
import sys
from pathlib import Path


def main():
    ROOT = Path(__file__).resolve().parent
    if str(ROOT) not in sys.path:
        # Ensures root is first in path for imports like 'config.settings'
        sys.path.insert(0, str(ROOT))

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        print("Warning: 'dotenv' not installed; skipping .env load. Install it for better env management.")
        pass  # Added a warning for better feedback in dev environments

    required_env = [
        'SECRET_KEY',
        'DATABASE_URL',
        'PGHOST',
        'PGPORT',
        'PGUSER',
        'PGPASSWORD',
        'STUDY_PGHOST',  # If different from main DB
        'STUDY_PGUSER',  # If different from main DB
        'STUDY_PGPASSWORD',  # If different from main DB
    ]
    missing = [var for var in required_env if not os.getenv(var)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in .env or via export/os.environ."
        )  # Improved error message for usability

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv(
        "DJANGO_SETTINGS_MODULE", "config.settings"))

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc  # Standard Django error handling for better diagnostics

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
