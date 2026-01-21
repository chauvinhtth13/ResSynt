"""
Management command to rotate Fernet encryption keys for encrypted fields.

Usage:
    1. Generate new key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    2. Update .env:
       - Set FIELD_ENCRYPTION_KEY=<new_key>
       - Set FIELD_ENCRYPTION_KEY_OLD=<current_key>
    3. Run: python manage.py rotate_encryption_keys --dry-run
    4. Run: python manage.py rotate_encryption_keys
    5. After success, remove FIELD_ENCRYPTION_KEY_OLD from .env

This command:
- Finds all models with EncryptedCharField/EncryptedTextField
- Re-saves each record to re-encrypt with the new primary key
- Logs progress and any errors
"""

import logging
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger("audit")


class Command(BaseCommand):
    help = "Re-encrypt all encrypted fields with the current primary Fernet key"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process in each batch (default: 100)",
        )
        parser.add_argument(
            "--model",
            type=str,
            help="Only process specific model (format: app_label.ModelName)",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        target_model = options.get("model")

        # Check if we have multiple keys (rotation in progress)
        if len(settings.FERNET_KEYS) < 2:
            self.stdout.write(
                self.style.WARNING(
                    "Only one Fernet key configured. "
                    "Set FIELD_ENCRYPTION_KEY_OLD to enable key rotation."
                )
            )
            if not dry_run:
                raise CommandError(
                    "Key rotation requires FIELD_ENCRYPTION_KEY_OLD to be set"
                )

        # Find all models with encrypted fields
        encrypted_models = self._find_encrypted_models(target_model)

        if not encrypted_models:
            self.stdout.write(self.style.WARNING("No encrypted fields found."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(encrypted_models)} model(s) with encrypted fields"
            )
        )

        total_processed = 0
        total_errors = 0

        for model, field_names in encrypted_models.items():
            model_label = f"{model._meta.app_label}.{model.__name__}"
            self.stdout.write(f"\nProcessing {model_label}...")
            self.stdout.write(f"  Encrypted fields: {', '.join(field_names)}")

            count = model.objects.count()
            self.stdout.write(f"  Total records: {count}")

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"  [DRY-RUN] Would re-encrypt {count} records")
                )
                continue

            processed, errors = self._process_model(model, field_names, batch_size)
            total_processed += processed
            total_errors += errors

            self.stdout.write(
                self.style.SUCCESS(f"  Processed: {processed}, Errors: {errors}")
            )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN complete. No changes made. "
                    "Run without --dry-run to apply changes."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Key rotation complete. "
                    f"Processed: {total_processed}, Errors: {total_errors}"
                )
            )
            if total_errors == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nYou can now remove FIELD_ENCRYPTION_KEY_OLD from .env"
                    )
                )
                logger.info(
                    "Encryption key rotation completed successfully",
                    extra={"processed": total_processed, "errors": total_errors},
                )

    def _find_encrypted_models(self, target_model: str | None) -> dict:
        """Find all models that have encrypted fields."""
        try:
            from encrypted_fields.fields import EncryptedFieldMixin
        except ImportError:
            raise CommandError(
                "django-fernet-encrypted-fields is not installed"
            )

        encrypted_models = {}

        for model in apps.get_models():
            # Filter by target model if specified
            if target_model:
                model_label = f"{model._meta.app_label}.{model.__name__}"
                if model_label.lower() != target_model.lower():
                    continue

            encrypted_fields = []
            for field in model._meta.get_fields():
                if hasattr(field, "__class__") and isinstance(
                    field, EncryptedFieldMixin
                ):
                    encrypted_fields.append(field.name)

            if encrypted_fields:
                encrypted_models[model] = encrypted_fields

        return encrypted_models

    def _process_model(
        self, model, field_names: list[str], batch_size: int
    ) -> tuple[int, int]:
        """Re-save all records in a model to re-encrypt with new key."""
        processed = 0
        errors = 0

        # Process in batches
        queryset = model.objects.all().order_by("pk")
        
        for obj in queryset.iterator(chunk_size=batch_size):
            try:
                with transaction.atomic():
                    # Simply saving will re-encrypt with the primary key
                    obj.save(update_fields=field_names)
                processed += 1
            except Exception as e:
                errors += 1
                logger.error(
                    f"Error re-encrypting {model.__name__} pk={obj.pk}: {e}",
                    exc_info=True,
                )
                self.stdout.write(
                    self.style.ERROR(f"    Error on pk={obj.pk}: {e}")
                )

        return processed, errors
