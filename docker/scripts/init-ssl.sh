#!/bin/bash
# =============================================================================
# INITIAL SETUP SCRIPT - Let's Encrypt SSL
# =============================================================================
# Usage: ./init-ssl.sh your-domain.com admin@your-domain.com
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2; }

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

log "Setting up SSL for domain: ${DOMAIN}"
log "Email for notifications: ${EMAIL}"

# Create required directories
log "Creating required directories..."
mkdir -p /data/ressynt/{postgres,redis,media,logs,nginx_logs}
mkdir -p /data/ressynt/certbot/{conf,www}

# Generate self-signed certificate for initial setup
log "Generating temporary self-signed certificate..."
NGINX_SSL_DIR="$(dirname "$0")/../nginx/ssl"
mkdir -p "${NGINX_SSL_DIR}"

if [ ! -f "${NGINX_SSL_DIR}/nginx-selfsigned.crt" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${NGINX_SSL_DIR}/nginx-selfsigned.key" \
        -out "${NGINX_SSL_DIR}/nginx-selfsigned.crt" \
        -subj "/CN=${DOMAIN}"
    log "Self-signed certificate created"
fi

# Update nginx config with actual domain
log "Updating nginx configuration..."
NGINX_CONF="$(dirname "$0")/../nginx/conf.d/default.conf"
sed -i "s/your-domain.com/${DOMAIN}/g" "${NGINX_CONF}"

# Start nginx with self-signed cert
log "Starting nginx..."
docker compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx to be ready
sleep 5

# Request Let's Encrypt certificate
log "Requesting Let's Encrypt certificate..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos --no-eff-email \
    -d "${DOMAIN}" -d "www.${DOMAIN}"

if [ $? -eq 0 ]; then
    log "Certificate obtained successfully!"
    
    # Update nginx config to use Let's Encrypt cert
    log "Updating nginx to use Let's Encrypt certificate..."
    sed -i "s|ssl_certificate /etc/nginx/ssl/nginx-selfsigned.crt;|# ssl_certificate /etc/nginx/ssl/nginx-selfsigned.crt;|g" "${NGINX_CONF}"
    sed -i "s|ssl_certificate_key /etc/nginx/ssl/nginx-selfsigned.key;|# ssl_certificate_key /etc/nginx/ssl/nginx-selfsigned.key;|g" "${NGINX_CONF}"
    sed -i "s|# ssl_certificate /etc/letsencrypt|ssl_certificate /etc/letsencrypt|g" "${NGINX_CONF}"
    sed -i "s|# ssl_certificate_key /etc/letsencrypt|ssl_certificate_key /etc/letsencrypt|g" "${NGINX_CONF}"
    
    # Reload nginx
    docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
    
    log "===== SSL Setup Complete ====="
    log "Your site is now available at: https://${DOMAIN}"
else
    error "Failed to obtain certificate!"
    warn "Your site is running with a self-signed certificate at: https://${DOMAIN}"
    warn "You can retry later with: docker compose run --rm certbot certonly ..."
fi
