#!/bin/bash
# ============================================
# Restore Database Backups
# ============================================
# Run this script AFTER docker-compose is up and databases are created
# Usage: docker exec -it ressynt_postgres /backups/restore_all.sh

set -e

echo "============================================"
echo "ResSynt Database Restore Script"
echo "============================================"

# Restore db_management
echo ""
echo "[1/3] Restoring db_management from backup_admin.sql..."
if [ -f /backups/backup_admin.sql ]; then
    psql -U ressynt_admin -d db_management -f /backups/backup_admin.sql
    echo "✓ db_management restored successfully"
else
    echo "✗ backup_admin.sql not found!"
    exit 1
fi

# Restore db_study_43en
echo ""
echo "[2/3] Restoring db_study_43en from backup_43en.sql..."
if [ -f /backups/backup_43en.sql ]; then
    psql -U ressynt_admin -d db_study_43en -f /backups/backup_43en.sql
    echo "✓ db_study_43en restored successfully"
else
    echo "✗ backup_43en.sql not found!"
    exit 1
fi

# Restore db_study_44en
echo ""
echo "[3/3] Restoring db_study_44en from backup_44en.sql..."
if [ -f /backups/backup_44en.sql ]; then
    psql -U ressynt_admin -d db_study_44en -f /backups/backup_44en.sql
    echo "✓ db_study_44en restored successfully"
else
    echo "✗ backup_44en.sql not found!"
    exit 1
fi

echo ""
echo "============================================"
echo "All databases restored successfully!"
echo "============================================"
