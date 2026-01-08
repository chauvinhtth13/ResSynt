#!/bin/bash
# =============================================================================
# RESTORE SCRIPT - PostgreSQL
# =============================================================================
# Usage: ./restore.sh <backup_file.sql.gz>
# =============================================================================

set -euo pipefail

# Load environment variables
if [ -f "$(dirname "$0")/../../.env.docker" ]; then
    source "$(dirname "$0")/../../.env.docker"
fi

# Container name
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ressynt-postgres}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2; }

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /data/ressynt/backups/postgres/ 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE=$1

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Validate environment
if [ -z "${PGUSER:-}" ]; then
    error "PGUSER must be set"
    exit 1
fi

# Warning
echo ""
echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                         WARNING                               ║${NC}"
echo -e "${RED}╠═══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║  This operation will OVERWRITE the current database!          ║${NC}"
echo -e "${RED}║  All existing data will be LOST!                              ║${NC}"
echo -e "${RED}║                                                               ║${NC}"
echo -e "${RED}║  Backup file: $(basename "$BACKUP_FILE")${NC}"
echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "Are you absolutely sure? Type 'yes' to confirm: " confirm

if [ "$confirm" != "yes" ]; then
    log "Restore cancelled."
    exit 0
fi

# Create pre-restore backup
log "Creating pre-restore backup..."
PRE_RESTORE_BACKUP="/data/ressynt/backups/postgres/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"

if docker exec "${POSTGRES_CONTAINER}" pg_dumpall -U "${PGUSER}" --clean --if-exists | gzip > "${PRE_RESTORE_BACKUP}"; then
    log "Pre-restore backup created: ${PRE_RESTORE_BACKUP}"
else
    warn "Failed to create pre-restore backup, continuing anyway..."
fi

# Stop dependent services
log "Stopping web and celery services..."
docker compose -f docker-compose.prod.yml stop web celery_worker celery_beat 2>/dev/null || true

# Restore database
log "Restoring database from backup..."

if gunzip -c "$BACKUP_FILE" | docker exec -i "${POSTGRES_CONTAINER}" psql -U "${PGUSER}"; then
    log "Database restore completed successfully!"
else
    error "Database restore failed!"
    log "You can restore the pre-restore backup: ${PRE_RESTORE_BACKUP}"
    exit 1
fi

# Restart services
log "Restarting services..."
docker compose -f docker-compose.prod.yml start web celery_worker celery_beat 2>/dev/null || true

log "===== Restore Summary ====="
log "Restored from: $BACKUP_FILE"
log "Pre-restore backup: ${PRE_RESTORE_BACKUP}"
log "Restore process completed!"
