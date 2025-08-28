#!/usr/bin/env python
# manage.py
import os
import sys
from pathlib import Path

def main():
    ROOT = Path(__file__).resolve().parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    required_env = ['SECRET_KEY', 'DATABASE_URL']  # Add critical vars
    missing = [var for var in required_env if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing env vars: {', '.join(missing)}")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"))

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()