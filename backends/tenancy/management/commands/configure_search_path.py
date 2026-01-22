"""
Management command to configure PostgreSQL user's default search_path.
This ensures future migrations go to the correct schema.
Usage: python manage.py configure_search_path
"""
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Configure PostgreSQL search_path for the database user"

    def handle(self, *args, **options):
        target_schema = getattr(settings, "MANAGEMENT_DB_SCHEMA", "management")
        db_user = settings.DATABASES["default"]["USER"]

        self.stdout.write(
            self.style.NOTICE(f"Database user: {db_user}")
        )
        self.stdout.write(
            self.style.NOTICE(f"Target schema: {target_schema}")
        )

        with connection.cursor() as cursor:
            # 1. Check current search_path
            cursor.execute("SHOW search_path;")
            current_path = cursor.fetchone()[0]
            self.stdout.write(f"\nCurrent search_path: {current_path}")

            # 2. Check if target schema exists
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [target_schema],
            )
            if not cursor.fetchone():
                self.stdout.write(
                    self.style.NOTICE(f"\nCreating schema '{target_schema}'...")
                )
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"')
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Schema '{target_schema}' created")
                )

            # 3. Set default search_path for the user
            self.stdout.write(
                self.style.NOTICE(
                    f"\nSetting default search_path for user '{db_user}'..."
                )
            )
            try:
                # Need to use format for role name, but it's from our own config
                cursor.execute(
                    f'ALTER ROLE "{db_user}" SET search_path TO "{target_schema}", public'
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Default search_path set to: {target_schema}, public"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Could not set search_path: {e}")
                )
                self.stdout.write(
                    self.style.WARNING(
                        "  You may need to run this command with a superuser."
                    )
                )
                return

            # 4. Verify in session
            cursor.execute(
                f"SET search_path TO \"{target_schema}\", public"
            )
            cursor.execute("SHOW search_path;")
            new_path = cursor.fetchone()[0]
            self.stdout.write(f"\nSession search_path: {new_path}")

            # 5. Summary
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Future migrations will create tables in '{target_schema}' schema"
                )
            )
            self.stdout.write(
                self.style.NOTICE(
                    "\nNote: Reconnect to database for changes to take effect."
                )
            )
