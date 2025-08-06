#!/usr/bin/env python
"""Manage script for ResSync (optimized)."""
import os
import sys
import logging

# Optional: load .env from project root (install python-dotenv in dev env)
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    # load .env only if present
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
except Exception:
    # dotenv is optional — fail silently in environments that don't use it
    pass

logger = logging.getLogger("manage")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    """Run administrative tasks."""
    # Default settings module — change to your default if needed
    default_settings = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.local")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)

    # Allow explicit override (useful in scripts/CI)
    override = os.environ.get("DJANGO_SETTINGS_MODULE_OVERRIDE")
    if override:
        os.environ["DJANGO_SETTINGS_MODULE"] = override
        logger.info("DJANGO_SETTINGS_MODULE overridden -> %s", override)

    try:
        # import here so ImportError surfaces with helpful message
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        msg = (
            "Couldn't import Django. Are you sure it's installed and available on your "
            "PYTHONPATH environment variable? Did you forget to activate a virtual environment?\n"
            "If you're in a virtualenv, try: `pip install -r requirements.txt`."
        )
        raise ImportError(msg) from exc

    # Helpful info about the command being executed
    if len(sys.argv) > 1:
        logger.info("manage.py %s (settings=%s)", " ".join(sys.argv[1:]), os.environ.get("DJANGO_SETTINGS_MODULE"))

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()