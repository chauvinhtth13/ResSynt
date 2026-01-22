"""
Management command to move tables from public schema to management schema.
Usage: python manage.py migrate_to_schema --dry-run (preview first)
       python manage.py migrate_to_schema (execute)
"""
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Move all tables from public schema to management schema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without executing",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        target_schema = getattr(settings, "MANAGEMENT_DB_SCHEMA", "management")
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(
            self.style.NOTICE(f"Target schema: {target_schema}")
        )

        with connection.cursor() as cursor:
            # 1. Check if target schema exists
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [target_schema],
            )
            if not cursor.fetchone():
                self.stdout.write(
                    self.style.ERROR(f"Schema '{target_schema}' does not exist!")
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"Create it first: CREATE SCHEMA {target_schema};"
                    )
                )
                return

            # 2. Get all tables currently in public schema
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            public_tables = [row[0] for row in cursor.fetchall()]

            if not public_tables:
                self.stdout.write(
                    self.style.SUCCESS("No tables in public schema to move!")
                )
                return

            # 3. Check which tables already exist in target schema
            cursor.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_type = 'BASE TABLE'
                """,
                [target_schema],
            )
            existing_tables = {row[0] for row in cursor.fetchall()}

            # 4. Display tables to be moved
            self.stdout.write("\nTables to move from 'public' to '%s':" % target_schema)
            tables_to_move = []
            for table in public_tables:
                if table in existing_tables:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ {table} (already exists in {target_schema}, will skip)")
                    )
                else:
                    self.stdout.write(self.style.HTTP_INFO(f"  → {table}"))
                    tables_to_move.append(table)

            if not tables_to_move:
                self.stdout.write(
                    self.style.WARNING("\nNo tables to move (all already exist in target schema)")
                )
                return

            self.stdout.write(f"\nTotal: {len(tables_to_move)} tables to move")

            if dry_run:
                self.stdout.write(
                    self.style.NOTICE("\n[DRY-RUN] SQL that would be executed:")
                )
                for table in tables_to_move:
                    self.stdout.write(
                        f"  ALTER TABLE public.{table} SET SCHEMA {target_schema};"
                    )
                self.stdout.write(
                    self.style.NOTICE("\nRun without --dry-run to execute.")
                )
                return

            # 5. Confirm before executing
            if not force:
                confirm = input(
                    f"\nMove {len(tables_to_move)} tables to '{target_schema}' schema? (yes/no): "
                )
                if confirm.lower() != "yes":
                    self.stdout.write(self.style.WARNING("Aborted."))
                    return

            # 6. Execute the move
            self.stdout.write(self.style.NOTICE("\nMoving tables..."))
            success_count = 0
            error_count = 0

            for table in tables_to_move:
                try:
                    # Use parameterized query where possible, but schema/table names need formatting
                    # We validate the table name comes from information_schema
                    cursor.execute(
                        f'ALTER TABLE public."{table}" SET SCHEMA "{target_schema}"'
                    )
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {table}"))
                    success_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ {table}: {e}"))
                    error_count += 1

            # 7. Summary
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully moved: {success_count} tables")
            )
            if error_count:
                self.stdout.write(
                    self.style.ERROR(f"Failed: {error_count} tables")
                )

            # 8. Update search_path reminder
            self.stdout.write(
                self.style.NOTICE(
                    f"\n✓ Tables are now in '{target_schema}' schema."
                    f"\nYour DATABASE OPTIONS already has search_path={target_schema},public"
                    "\nso Django should find them correctly."
                )
            )
