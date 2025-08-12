from django.core.management.base import BaseCommand
from django.db import connections
from apps.tenancy.models import Study

class Command(BaseCommand):
    help = "Tạo nghiên cứu mới + DB riêng."

    def add_arguments(self, parser):
        parser.add_argument("code", type=str)
        parser.add_argument("name", type=str)
        parser.add_argument("db_alias", type=str)

    def handle(self, *args, **options):
        code = options["code"]
        name = options["name"]
        db_alias = options["db_alias"]

        if Study.objects.using("db_management").filter(code=code).exists():
            self.stdout.write(self.style.ERROR("Study code đã tồn tại."))
            return

        # Tạo DB vật lý (chạy lệnh trực tiếp trong Postgres)
        with connections["db_management"].cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{db_alias}";')

        Study.objects.using("db_management").create(
            code=code, name=name, database_name=db_alias, status="active"
        )

        self.stdout.write(self.style.SUCCESS(f"Tạo study {code} thành công."))
