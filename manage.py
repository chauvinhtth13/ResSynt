#!/usr/bin/env python
# manage.py
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def main():
    # === Define project root ===
    ROOT = Path(__file__).resolve().parent

    # Ensure project root in sys.path (to prevent import errors)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # === Load .env if exists ===
    try:
        from dotenv import load_dotenv  # pip install python-dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass  # Skip if dotenv not installed
    except Exception as e:
        print(f"Warning: cannot load .env - {e}")

    # === Configure DJANGO_SETTINGS_MODULE ===
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "config.settings")
    )

    # === Run Django command ===
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Cannot import Django. Make sure Django is installed "
            "and PYTHONPATH is correct."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()