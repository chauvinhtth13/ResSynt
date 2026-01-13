#!/usr/bin/env python
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connections

# Check db_study_43en
print("=== Checking db_study_43en ===")
with connections['db_study_43en'].cursor() as cursor:
    sql = """
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema IN ('log', 'logging') 
        AND table_name LIKE 'audit%%' 
        ORDER BY table_schema, table_name
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    if results:
        for schema, table in results:
            print(f"  {schema}.{table}")
    else:
        print("  No audit tables found in 'log' or 'logging' schemas")

print("\n=== Checking db_study_44en ===")
with connections['db_study_44en'].cursor() as cursor:
    sql = """
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema IN ('log', 'logging') 
        AND table_name LIKE 'audit%%' 
        ORDER BY table_schema, table_name
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    if results:
        for schema, table in results:
            print(f"  {schema}.{table}")
    else:
        print("  No audit tables found in 'log' or 'logging' schemas")

# Check if AuditLog model points to correct table
print("\n=== Model Configuration ===")
from backends.studies.study_43en.models import AuditLog, AuditLogDetail
print(f"study_43en AuditLog table: {AuditLog._meta.db_table}")
print(f"study_43en AuditLogDetail table: {AuditLogDetail._meta.db_table}")

from backends.studies.study_44en.models import AuditLog as AuditLog44, AuditLogDetail as AuditLogDetail44
print(f"study_44en AuditLog table: {AuditLog44._meta.db_table}")
print(f"study_44en AuditLogDetail table: {AuditLogDetail44._meta.db_table}")
