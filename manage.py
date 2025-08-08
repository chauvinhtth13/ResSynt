#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def main():
    # Thêm project root vào sys.path để import ổn định
    ROOT = Path(__file__).resolve().parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # Load .env nếu có (không bắt buộc nhưng nên có)
    try:
        from dotenv import load_dotenv  # pip install python-dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass  # không có dotenv cũng không sao

    # Cho phép override qua biến môi trường; mặc định dùng config.settings
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "config.settings")
    )

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()