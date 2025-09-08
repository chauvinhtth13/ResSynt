from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from axes.utils import reset

User = get_user_model()


class Command(BaseCommand):
    help = "Unlock a user account locked by axes"

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            type=str,
            help="Username to unlock",
        )
        parser.add_argument(
            "--reset-status",
            action="store_true",
            help="Also reset user status to active (if status field exists)",
        )

    def handle(self, *args, **options):
        username = options["username"]

        # Reset axes lockout
        reset(username=username)

        # Reset user status if requested
        if options["reset_status"]:
            try:
                user = User.objects.get(username=username)

                # Check if user has status field before updating
                if hasattr(user, "status"):
                    user.status = "active"  # type: ignore[attr-defined]

                # Reset failed attempts if field exists
                if hasattr(user, "failed_login_attempts"):
                    user.failed_login_attempts = 0  # type: ignore[attr-defined]

                user.save()

                self.stdout.write(
                    self.style.SUCCESS(f"User {username} unlocked and reset")
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"User {username} not found, but axes lockout cleared")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Axes lockout cleared for {username}")
            )