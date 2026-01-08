#!/bin/bash
# =============================================================================
# BACKUP SCRIPT - PostgreSQL & Redis
# =============================================================================
# Usage: ./backup.sh
# Cron: 0 2 * * * /path/to/docker/scripts/backup.sh >> /var/log/ressynt-backup.log 2>&1
# =============================================================================

set -euo pipefail

# Load environment variables
if [ -f "$(dirname "$0")/../../.env.docker" ]; then
    source "$(dirname "$0")/../../.env.docker"
fi

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/data/ressynt/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ressynt-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ressynt-redis}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2; }

# Validate environment
if [ -z "${PGUSER:-}" ] || [ -z "${PGPASSWORD:-}" ]; then
    error "PGUSER and PGPASSWORD must be set"
    exit 1
fi

# Create backup directories
mkdir -p "${BACKUP_DIR}/postgres" "${BACKUP_DIR}/redis"

log "Starting backup process..."

# -----------------------------------------------------------------------------
# PostgreSQL Backup
# -----------------------------------------------------------------------------
log "Starting PostgreSQL backup..."

POSTGRES_BACKUP="${BACKUP_DIR}/postgres/backup_${DATE}.sql.gz"

if docker exec "${POSTGRES_CONTAINER}" pg_dumpall -U "${PGUSER}" --clean --if-exists | gzip > "${POSTGRES_BACKUP}"; then
    BACKUP_SIZE=$(du -h "${POSTGRES_BACKUP}" | cut -f1)
    log "PostgreSQL backup completed: backup_${DATE}.sql.gz (${BACKUP_SIZE})"
else
    error "PostgreSQL backup failed!"
    exit 1
fi

# -----------------------------------------------------------------------------
# Redis Backup
# -----------------------------------------------------------------------------
log "Starting Redis backup..."

REDIS_BACKUP="${BACKUP_DIR}/redis/dump_${DATE}.rdb"

if [ -n "${REDIS_PASSWORD:-}" ]; then
    REDIS_AUTH="-a ${REDIS_PASSWORD}"
else
    REDIS_AUTH=""
fi

# Trigger BGSAVE
if docker exec "${REDIS_CONTAINER}" redis-cli ${REDIS_AUTH} BGSAVE >/dev/null 2>&1; then
    # Wait for background save to complete
    sleep 5
    
    # Copy dump file
    if docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "${REDIS_BACKUP}" 2>/dev/null; then
        BACKUP_SIZE=$(du -h "${REDIS_BACKUP}" | cut -f1)
        log "Redis backup completed: dump_${DATE}.rdb (${BACKUP_SIZE})"
    else
        warn "Redis backup file not found (may be empty database)"
    fi
else
    warn "Redis BGSAVE command failed (Redis may not be running or auth failed)"
fi

# -----------------------------------------------------------------------------
# Cleanup old backups
# -----------------------------------------------------------------------------
log "Cleaning up backups older than ${RETENTION_DAYS} days..."

DELETED_COUNT=$(find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)

if [ "${DELETED_COUNT}" -gt 0 ]; then
    log "Deleted ${DELETED_COUNT} old backup file(s)"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
log "===== Backup Summary ====="
log "PostgreSQL: ${POSTGRES_BACKUP}"
if [ -f "${REDIS_BACKUP}" ]; then
    log "Redis: ${REDIS_BACKUP}"
fi
log "Retention: ${RETENTION_DAYS} days"
log "Backup process completed successfully!"
