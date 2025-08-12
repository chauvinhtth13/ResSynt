#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def main():
    # === Xác định project root ===
    ROOT = Path(__file__).resolve().parent

    # Đảm bảo project root trong sys.path (đề phòng lỗi import)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # === Load .env nếu có ===
    try:
        from dotenv import load_dotenv  # pip install python-dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass  # không cài dotenv thì bỏ qua
    except Exception as e:
        print(f"Warning: cannot load .env - {e}")

    # === Cấu hình DJANGO_SETTINGS_MODULE ===
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "config.settings")
    )

    # === Chạy Django command ===
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Không thể import Django. Hãy chắc chắn rằng Django đã được cài đặt "
            "và PYTHONPATH đã đúng."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()