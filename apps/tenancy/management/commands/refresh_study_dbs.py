# apps/tenancy/management/commands/refresh_study_dbs.py
from django.core.management.base import BaseCommand
from apps.tenancy.db_loader import load_study_dbs

class Command(BaseCommand):
    help = "Load/refresh active study databases from metadata."

    def handle(self, *args, **options):
        load_study_dbs()
        self.stdout.write(self.style.SUCCESS("Refreshed active study DBs."))
        self.stdout.write("Check logs for details.")
        # Thông báo này sẽ hiển thị trong terminal khi chạy lệnh