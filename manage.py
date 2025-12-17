#!/usr/bin/env python
"""Django management script."""
import os
import sys
from pathlib import Path
import environ
from django.core.management import execute_from_command_line


def main():
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Load .env file
    try:
        environ.Env.read_env(root / ".env")
    except ImportError:
        pass
    except (OSError, ValueError, environ.ImproperlyConfigured) as e:
        print(f"Warning: Failed to load .env: {e}")

    # Set defaults for Django settings
    os.environ.setdefault("DJANGO_ENV", "dev")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
