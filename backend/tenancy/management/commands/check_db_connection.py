# backend/tenancy/management/commands/check_db_connection.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Check database connection and schema'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check current database
            cursor.execute("SELECT current_database()")
            result = cursor.fetchone()
            if result:
                db_name = result[0]
                self.stdout.write(f"Connected to database: {db_name}")
            else:
                self.stdout.write("Failed to retrieve database name")
            
            # Check current schema
            cursor.execute("SELECT current_schema()")
            result = cursor.fetchone()
            if result:
                schema = result[0]
                self.stdout.write(f"Current schema: {schema}")
            else:
                self.stdout.write("Failed to retrieve schema")
            
            # List all schemas
            cursor.execute("SELECT schema_name FROM information_schema.schemata")
            schemas = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"Available schemas: {', '.join(schemas)}")