# Docker Security Configuration Guide - ResSynt

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Dockerfile - Multi-stage Build](#2-dockerfile---multi-stage-build)
3. [Docker Compose - Production](#3-docker-compose---production)
4. [Docker Compose - Development](#4-docker-compose---development)
5. [Nginx Reverse Proxy](#5-nginx-reverse-proxy)
6. [Security Best Practices](#6-security-best-practices)
7. [Secrets Management](#7-secrets-management)
8. [Health Checks & Monitoring](#8-health-checks--monitoring)
9. [Backup & Recovery](#9-backup--recovery)
10. [Commands Reference](#10-commands-reference)

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRODUCTION ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌──────────────┐                                                         │
│    │   Internet   │                                                         │
│    └──────┬───────┘                                                         │
│           │                                                                 │
│           ▼                                                                 │
│    ┌──────────────┐    ┌──────────────┐                                     │
│    │    Nginx     │◄───│  Let's Encrypt│  (SSL/TLS Termination)             │
│    │   Reverse    │    │   Certbot    │                                     │
│    │    Proxy     │    └──────────────┘                                     │
│    └──────┬───────┘                                                         │
│           │                                                                 │
│           ▼                                                                 │
│    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                │
│    │   Gunicorn   │    │    Celery    │    │    Celery    │                │
│    │   (Django)   │    │   Worker     │    │    Beat      │                │
│    │   Container  │    │  Container   │    │  Container   │                │
│    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                │
│           │                   │                   │                         │
│           └───────────┬───────┴───────────────────┘                         │
│                       │                                                     │
│           ┌───────────┴───────────┐                                         │
│           │                       │                                         │
│           ▼                       ▼                                         │
│    ┌──────────────┐        ┌──────────────┐                                 │
│    │  PostgreSQL  │        │    Redis     │                                 │
│    │  Container   │        │  Container   │                                 │
│    │   (Data)     │        │   (Cache)    │                                 │
│    └──────────────┘        └──────────────┘                                 │
│           │                       │                                         │
│           ▼                       ▼                                         │
│    ┌──────────────┐        ┌──────────────┐                                 │
│    │   Volume     │        │   Volume     │                                 │
│    │  postgres_   │        │   redis_     │                                 │
│    │    data      │        │    data      │                                 │
│    └──────────────┘        └──────────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Services Overview

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **web** | Custom Django | 8000 (internal) | Django + Gunicorn |
| **postgres** | postgres:16-alpine | 5432 (internal) | Database |
| **redis** | redis:7-alpine | 6379 (internal) | Cache + Broker |
| **celery_worker** | Custom Django | - | Async tasks |
| **celery_beat** | Custom Django | - | Scheduled tasks |
| **nginx** | nginx:alpine | 80, 443 | Reverse proxy |

---

## 2. Dockerfile - Multi-stage Build

### Tạo file `Dockerfile`

```dockerfile
# =============================================================================
# DOCKERFILE - ResSynt Django Application
# Multi-stage build for security and optimization
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base image with Python
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS python-base

# Environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# -----------------------------------------------------------------------------
# Stage 2: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python-base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and use virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 3: Production image
# -----------------------------------------------------------------------------
FROM python-base AS production

# Security: Create non-root user with specific UID/GID
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/mediafiles && \
    chown -R appuser:appgroup /app/logs /app/staticfiles /app/mediafiles

# Security: Remove unnecessary files
RUN rm -rf \
    .git \
    .github \
    .vscode \
    tests \
    docs \
    *.md \
    docker-compose*.yml \
    Dockerfile* \
    .env* \
    Makefile \
    .gitignore \
    .dockerignore

# Collect static files (requires SECRET_KEY)
ARG SECRET_KEY_BUILD="build-time-secret-key-at-least-50-characters-long!"
RUN DJANGO_ENV=prod SECRET_KEY="$SECRET_KEY_BUILD" \
    python manage.py collectstatic --noinput --clear

# Security: Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance"]

# -----------------------------------------------------------------------------
# Stage 4: Development image (optional, for local development)
# -----------------------------------------------------------------------------
FROM python-base AS development

# Install dev dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dev tools
RUN pip install django-debug-toolbar ipython

WORKDIR /app

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Tạo file `.dockerignore`

```dockerignore
# =============================================================================
# .dockerignore - Files to exclude from Docker build context
# =============================================================================

# Git
.git
.gitattributes
.gitignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
.eggs/
*.egg

# Virtual environments
venv/
.venv/
env/

# Environment files
.env
.env.local
.env.*.local

# Docker
Dockerfile*
docker-compose*.yml
.docker/

# Documentation
docs/
*.md
README*
LICENSE*

# Tests
tests/
test_*.py
*_test.py
conftest.py

# Build artifacts
dist/
build/
*.manifest
*.spec

# Logs (will be mounted as volumes)
logs/
*.log

# Static/Media (collected during build)
staticfiles/
mediafiles/

# Development
Makefile
.editorconfig
.pre-commit-config.yaml

# OS
.DS_Store
Thumbs.db
```

---

## 3. Docker Compose - Production

### Tạo file `docker-compose.prod.yml`

```yaml
# =============================================================================
# DOCKER COMPOSE - PRODUCTION
# =============================================================================
# Usage: docker compose -f docker-compose.prod.yml up -d
# =============================================================================

name: ressynt-prod

services:
  # ---------------------------------------------------------------------------
  # PostgreSQL Database
  # ---------------------------------------------------------------------------
  postgres:
    image: postgres:16-alpine
    container_name: ressynt-postgres
    restart: unless-stopped
    
    environment:
      POSTGRES_DB: ${PGDATABASE:-db_management}
      POSTGRES_USER: ${PGUSER}
      POSTGRES_PASSWORD: ${PGPASSWORD}
      # Security: Disable trust authentication
      POSTGRES_HOST_AUTH_METHOD: scram-sha-256
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256 --auth-local=scram-sha-256"
    
    volumes:
      - postgres_data:/var/lib/postgresql/data
      # Custom configuration
      - ./docker/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./docker/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
    
    # Security: Use custom config
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PGUSER} -d ${PGDATABASE}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    
    networks:
      - backend
    
    # Security: No external ports exposed
    # Access only through internal network

  # ---------------------------------------------------------------------------
  # Redis Cache & Broker
  # ---------------------------------------------------------------------------
  redis:
    image: redis:7-alpine
    container_name: ressynt-redis
    restart: unless-stopped
    
    # Security: Run with custom config and password
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
      --tcp-backlog 511
      --timeout 0
      --tcp-keepalive 300
      --loglevel notice
      --protected-mode yes
      --rename-command FLUSHDB ""
      --rename-command FLUSHALL ""
      --rename-command DEBUG ""
      --rename-command SHUTDOWN ""
    
    volumes:
      - redis_data:/data
    
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
    
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    
    networks:
      - backend
    
    # Security: No external ports

  # ---------------------------------------------------------------------------
  # Django Web Application
  # ---------------------------------------------------------------------------
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    image: ressynt-web:latest
    container_name: ressynt-web
    restart: unless-stopped
    
    environment:
      DJANGO_ENV: prod
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
      ALLOWED_HOSTS: ${ALLOWED_HOSTS}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS}
      
      # Database
      PGDATABASE: ${PGDATABASE:-db_management}
      PGUSER: ${PGUSER}
      PGPASSWORD: ${PGPASSWORD}
      PGHOST: postgres
      PGPORT: 5432
      
      # Redis
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      CELERY_BROKER_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
      CELERY_RESULT_BACKEND: redis://:${REDIS_PASSWORD}@redis:6379/2
      
      # Email
      EMAIL_HOST: ${EMAIL_HOST}
      EMAIL_PORT: ${EMAIL_PORT}
      EMAIL_HOST_USER: ${EMAIL_HOST_USER}
      EMAIL_HOST_PASSWORD: ${EMAIL_HOST_PASSWORD}
      DEFAULT_FROM_EMAIL: ${DEFAULT_FROM_EMAIL}
      
      # Security
      BACKUP_ENCRYPTION_PASSWORD: ${BACKUP_ENCRYPTION_PASSWORD}
      FIELD_ENCRYPTION_KEY: ${FIELD_ENCRYPTION_KEY}
    
    volumes:
      - static_files:/app/staticfiles:ro
      - media_files:/app/mediafiles
      - app_logs:/app/logs
    
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    # Security: Read-only filesystem where possible
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
      - /dev/shm:size=100M,mode=1777
    
    # Security: Drop all capabilities, add only needed
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    
    # Security: No privilege escalation
    security_opt:
      - no-new-privileges:true
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    
    networks:
      - backend
      - frontend

  # ---------------------------------------------------------------------------
  # Celery Worker
  # ---------------------------------------------------------------------------
  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    image: ressynt-web:latest
    container_name: ressynt-celery-worker
    restart: unless-stopped
    
    command: >
      celery -A config worker
      --loglevel=INFO
      --concurrency=4
      --max-tasks-per-child=100
      --prefetch-multiplier=4
      -Q default,high,low
    
    environment:
      DJANGO_ENV: prod
      SECRET_KEY: ${SECRET_KEY}
      PGDATABASE: ${PGDATABASE:-db_management}
      PGUSER: ${PGUSER}
      PGPASSWORD: ${PGPASSWORD}
      PGHOST: postgres
      PGPORT: 5432
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      CELERY_BROKER_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
      CELERY_RESULT_BACKEND: redis://:${REDIS_PASSWORD}@redis:6379/2
      BACKUP_ENCRYPTION_PASSWORD: ${BACKUP_ENCRYPTION_PASSWORD}
      FIELD_ENCRYPTION_KEY: ${FIELD_ENCRYPTION_KEY}
    
    volumes:
      - media_files:/app/mediafiles
      - app_logs:/app/logs
    
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      web:
        condition: service_healthy
    
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
    
    cap_drop:
      - ALL
    
    security_opt:
      - no-new-privileges:true
    
    healthcheck:
      test: ["CMD", "celery", "-A", "config", "inspect", "ping", "-d", "celery@$$HOSTNAME"]
      interval: 60s
      timeout: 30s
      retries: 3
      start_period: 60s
    
    networks:
      - backend

  # ---------------------------------------------------------------------------
  # Celery Beat (Scheduler)
  # ---------------------------------------------------------------------------
  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    image: ressynt-web:latest
    container_name: ressynt-celery-beat
    restart: unless-stopped
    
    command: >
      celery -A config beat
      --loglevel=INFO
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    
    environment:
      DJANGO_ENV: prod
      SECRET_KEY: ${SECRET_KEY}
      PGDATABASE: ${PGDATABASE:-db_management}
      PGUSER: ${PGUSER}
      PGPASSWORD: ${PGPASSWORD}
      PGHOST: postgres
      PGPORT: 5432
      CELERY_BROKER_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
      CELERY_RESULT_BACKEND: redis://:${REDIS_PASSWORD}@redis:6379/2
    
    volumes:
      - app_logs:/app/logs
    
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 128M
    
    read_only: true
    tmpfs:
      - /tmp:size=50M,mode=1777
    
    cap_drop:
      - ALL
    
    security_opt:
      - no-new-privileges:true
    
    networks:
      - backend

  # ---------------------------------------------------------------------------
  # Nginx Reverse Proxy
  # ---------------------------------------------------------------------------
  nginx:
    image: nginx:1.25-alpine
    container_name: ressynt-nginx
    restart: unless-stopped
    
    ports:
      - "80:80"
      - "443:443"
    
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/conf.d:/etc/nginx/conf.d:ro
      - static_files:/var/www/static:ro
      - media_files:/var/www/media:ro
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
      - nginx_logs:/var/log/nginx
    
    depends_on:
      - web
    
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 64M
    
    # Security: Drop unnecessary capabilities
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
      - CHOWN
      - SETGID
      - SETUID
    
    security_opt:
      - no-new-privileges:true
    
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
    
    networks:
      - frontend

  # ---------------------------------------------------------------------------
  # Certbot (Let's Encrypt SSL)
  # ---------------------------------------------------------------------------
  certbot:
    image: certbot/certbot:latest
    container_name: ressynt-certbot
    
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    
    # Renew certificates every 12 hours
    entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew --quiet; sleep 12h & wait $${!}; done"
    
    depends_on:
      - nginx

# =============================================================================
# Networks
# =============================================================================
networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
  
  backend:
    driver: bridge
    internal: true  # Security: No external access
    ipam:
      config:
        - subnet: 172.21.0.0/24

# =============================================================================
# Volumes
# =============================================================================
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/postgres
  
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/redis
  
  static_files:
    driver: local
  
  media_files:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/media
  
  app_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/logs
  
  nginx_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/nginx_logs
  
  certbot_conf:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/certbot/conf
  
  certbot_www:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/ressynt/certbot/www
```

---

## 4. Docker Compose - Development

### Tạo file `docker-compose.dev.yml`

```yaml
# =============================================================================
# DOCKER COMPOSE - DEVELOPMENT
# =============================================================================
# Usage: docker compose -f docker-compose.dev.yml up
# =============================================================================

name: ressynt-dev

services:
  # ---------------------------------------------------------------------------
  # PostgreSQL Database (Development)
  # ---------------------------------------------------------------------------
  postgres:
    image: postgres:16-alpine
    container_name: ressynt-postgres-dev
    
    environment:
      POSTGRES_DB: ${PGDATABASE:-db_management}
      POSTGRES_USER: ${PGUSER:-postgres}
      POSTGRES_PASSWORD: ${PGPASSWORD:-postgres}
    
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    
    ports:
      - "5432:5432"  # Exposed for local development tools
    
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PGUSER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ---------------------------------------------------------------------------
  # Redis (Development - Optional)
  # ---------------------------------------------------------------------------
  redis:
    image: redis:7-alpine
    container_name: ressynt-redis-dev
    
    ports:
      - "6379:6379"
    
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ---------------------------------------------------------------------------
  # Django Development Server
  # ---------------------------------------------------------------------------
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    container_name: ressynt-web-dev
    
    environment:
      DJANGO_ENV: dev
      SECRET_KEY: ${SECRET_KEY:-dev-secret-key-for-local-development-only-12345}
      DEBUG: "True"
      ALLOWED_HOSTS: localhost,127.0.0.1,0.0.0.0
      PGDATABASE: ${PGDATABASE:-db_management}
      PGUSER: ${PGUSER:-postgres}
      PGPASSWORD: ${PGPASSWORD:-postgres}
      PGHOST: postgres
      PGPORT: 5432
      # Redis optional in dev
      # REDIS_URL: redis://redis:6379/0
    
    volumes:
      # Mount source code for hot reload
      - .:/app
      # Exclude these directories from mount
      - /app/__pycache__
      - /app/.git
    
    ports:
      - "8000:8000"
    
    depends_on:
      postgres:
        condition: service_healthy
    
    # Development: Allow interactive debugging
    stdin_open: true
    tty: true

volumes:
  postgres_dev_data:
```

---

## 5. Nginx Reverse Proxy

### Tạo thư mục cấu hình

```bash
mkdir -p docker/nginx/conf.d
```

### Tạo file `docker/nginx/nginx.conf`

```nginx
# =============================================================================
# NGINX MAIN CONFIGURATION - Security Hardened
# =============================================================================

user nginx;
worker_processes auto;
pid /var/run/nginx.pid;

# Security: Limit information disclosure
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    # ==========================================================================
    # BASIC SETTINGS
    # ==========================================================================
    
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';
    
    access_log /var/log/nginx/access.log main;
    
    # ==========================================================================
    # PERFORMANCE
    # ==========================================================================
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript 
               application/xml application/rss+xml application/atom+xml image/svg+xml;
    
    # ==========================================================================
    # SECURITY HARDENING
    # ==========================================================================
    
    # Hide Nginx version
    server_tokens off;
    
    # Prevent clickjacking
    add_header X-Frame-Options "DENY" always;
    
    # Prevent MIME type sniffing
    add_header X-Content-Type-Options "nosniff" always;
    
    # XSS Protection
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Referrer Policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Permissions Policy
    add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;
    
    # Limit request body size
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    
    # Timeout settings
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;
    
    # Limit simultaneous connections
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
    limit_req_zone $binary_remote_addr zone=req_limit:10m rate=10r/s;
    
    # ==========================================================================
    # SSL CONFIGURATION
    # ==========================================================================
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # ==========================================================================
    # UPSTREAM
    # ==========================================================================
    
    upstream django {
        server web:8000;
        keepalive 32;
    }
    
    # ==========================================================================
    # INCLUDE VIRTUAL HOSTS
    # ==========================================================================
    
    include /etc/nginx/conf.d/*.conf;
}
```

### Tạo file `docker/nginx/conf.d/default.conf`

```nginx
# =============================================================================
# NGINX VIRTUAL HOST - ResSynt
# =============================================================================

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;  # CHANGE THIS
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Rate limiting
    limit_conn conn_limit 20;
    limit_req zone=req_limit burst=20 nodelay;
    
    # ==========================================================================
    # LOCATIONS
    # ==========================================================================
    
    # Static files
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff" always;
        
        # Security: Block access to sensitive file types
        location ~* \.(py|pyc|pyo|env|git|log)$ {
            deny all;
            return 404;
        }
    }
    
    # Media files
    location /media/ {
        alias /var/www/media/;
        expires 7d;
        add_header Cache-Control "public";
        add_header X-Content-Type-Options "nosniff" always;
        
        # Security: Disable script execution
        location ~* \.(php|py|pl|sh|bash|cgi)$ {
            deny all;
            return 404;
        }
    }
    
    # Health check (no logging)
    location /health/ {
        access_log off;
        proxy_pass http://django;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Django application
    location / {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # ==========================================================================
    # SECURITY - Block sensitive paths
    # ==========================================================================
    
    location ~ /\. {
        deny all;
        return 404;
    }
    
    location ~ ^/(admin|api)/.*\.(php|asp|aspx|jsp)$ {
        deny all;
        return 404;
    }
    
    # Block common attack paths
    location ~* (eval\(|base64_|union.*select|concat.*\() {
        deny all;
        return 403;
    }
}
```

---

## 6. Security Best Practices

### 6.1 Container Security Checklist

| Category | Practice | Status |
|----------|----------|--------|
| **Image** | Use official base images | ✅ |
| **Image** | Multi-stage builds (smaller attack surface) | ✅ |
| **Image** | Pin image versions (avoid `latest`) | ✅ |
| **Image** | Scan images for vulnerabilities | ⚠️ |
| **User** | Run as non-root user | ✅ |
| **User** | Use specific UID/GID | ✅ |
| **Filesystem** | Read-only root filesystem | ✅ |
| **Filesystem** | Use tmpfs for temp files | ✅ |
| **Network** | Internal network for databases | ✅ |
| **Network** | No exposed ports for internal services | ✅ |
| **Capabilities** | Drop all capabilities by default | ✅ |
| **Capabilities** | Add only required capabilities | ✅ |
| **Privileges** | No privilege escalation | ✅ |
| **Resources** | CPU/Memory limits | ✅ |
| **Health** | Health checks for all services | ✅ |
| **Secrets** | Use Docker secrets or env files | ✅ |
| **Logging** | Centralized logging | ✅ |

### 6.2 PostgreSQL Security

Tạo file `docker/postgres/postgresql.conf`:

```ini
# =============================================================================
# PostgreSQL Configuration - Security Hardened
# =============================================================================

# Connection Settings
listen_addresses = '*'
port = 5432
max_connections = 100

# Memory
shared_buffers = 256MB
work_mem = 16MB
maintenance_work_mem = 64MB

# Security
ssl = off  # SSL handled by Docker network (internal only)
password_encryption = scram-sha-256

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_truncate_on_rotation = on
log_rotation_age = 1d
log_rotation_size = 100MB

log_min_messages = warning
log_min_error_statement = error
log_min_duration_statement = 1000  # Log queries > 1s

log_connections = on
log_disconnections = on
log_hostname = off
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'ddl'  # Log DDL statements

# Performance
effective_cache_size = 768MB
random_page_cost = 1.1
effective_io_concurrency = 200

# Checkpoints
checkpoint_completion_target = 0.9
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB
```

Tạo file `docker/postgres/pg_hba.conf`:

```
# =============================================================================
# PostgreSQL Host-Based Authentication
# =============================================================================
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             all                                     scram-sha-256

# IPv4 connections from Docker network only
host    all             all             172.21.0.0/24           scram-sha-256

# Reject all other connections
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
```

### 6.3 Redis Security

Các biện pháp bảo mật đã cấu hình trong `docker-compose.prod.yml`:

```yaml
command: >
  redis-server
  --requirepass ${REDIS_PASSWORD}           # Require password
  --maxmemory 512mb                         # Memory limit
  --maxmemory-policy allkeys-lru           # Eviction policy
  --protected-mode yes                      # Reject external connections
  --rename-command FLUSHDB ""               # Disable dangerous commands
  --rename-command FLUSHALL ""
  --rename-command DEBUG ""
  --rename-command SHUTDOWN ""
```

---

## 7. Secrets Management

### 7.1 Tạo file `.env.docker`

```bash
# =============================================================================
# DOCKER ENVIRONMENT VARIABLES - PRODUCTION
# =============================================================================
# Copy to .env.docker and fill in values
# NEVER commit this file to git!
# =============================================================================

# Django
DJANGO_ENV=prod
SECRET_KEY=your-very-long-secret-key-at-least-50-characters-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# PostgreSQL
PGDATABASE=db_management
PGUSER=ressynt_user
PGPASSWORD=very-strong-database-password-here
PGHOST=postgres
PGPORT=5432

# Redis
REDIS_PASSWORD=very-strong-redis-password-here

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com

# Encryption
FIELD_ENCRYPTION_KEY=your-fernet-key-here
BACKUP_ENCRYPTION_PASSWORD=very-strong-backup-password

# SSL
DOMAIN_NAME=your-domain.com
```

### 7.2 Docker Secrets (Optional - For Swarm)

```yaml
# docker-compose.secrets.yml
secrets:
  db_password:
    external: true
  redis_password:
    external: true
  secret_key:
    external: true

services:
  web:
    secrets:
      - db_password
      - redis_password
      - secret_key
    environment:
      PGPASSWORD_FILE: /run/secrets/db_password
      REDIS_PASSWORD_FILE: /run/secrets/redis_password
      SECRET_KEY_FILE: /run/secrets/secret_key
```

---

## 8. Health Checks & Monitoring

### 8.1 Django Health Check Endpoint

Đã cấu hình trong `base.py`:

```python
THIRD_PARTY_APPS = [
    # ...
    "health_check",
    "health_check.db",
    "health_check.cache",
]
```

Thêm URL trong `config/urls/base.py`:

```python
urlpatterns = [
    # ...
    path('health/', include('health_check.urls')),
]
```

### 8.2 Monitoring Stack (Optional)

Tạo file `docker-compose.monitoring.yml`:

```yaml
# =============================================================================
# MONITORING STACK
# =============================================================================

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: ressynt-prometheus
    restart: unless-stopped
    
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: ressynt-grafana
    restart: unless-stopped
    
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: false
    
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/provisioning:/etc/grafana/provisioning:ro
    
    ports:
      - "3000:3000"
    
    networks:
      - monitoring

  node_exporter:
    image: prom/node-exporter:latest
    container_name: ressynt-node-exporter
    restart: unless-stopped
    
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
```

---

## 9. Backup & Recovery

### 9.1 Backup Script

Tạo file `docker/scripts/backup.sh`:

```bash
#!/bin/bash
# =============================================================================
# BACKUP SCRIPT - PostgreSQL & Redis
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="/data/ressynt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2; }

# Create backup directory
mkdir -p "${BACKUP_DIR}/postgres" "${BACKUP_DIR}/redis"

# -----------------------------------------------------------------------------
# PostgreSQL Backup
# -----------------------------------------------------------------------------
log "Starting PostgreSQL backup..."

docker exec ressynt-postgres pg_dumpall \
    -U "${PGUSER}" \
    --clean \
    --if-exists \
    | gzip > "${BACKUP_DIR}/postgres/backup_${DATE}.sql.gz"

if [ $? -eq 0 ]; then
    log "PostgreSQL backup completed: backup_${DATE}.sql.gz"
else
    error "PostgreSQL backup failed!"
    exit 1
fi

# -----------------------------------------------------------------------------
# Redis Backup
# -----------------------------------------------------------------------------
log "Starting Redis backup..."

docker exec ressynt-redis redis-cli -a "${REDIS_PASSWORD}" BGSAVE
sleep 5  # Wait for BGSAVE to complete

docker cp ressynt-redis:/data/dump.rdb "${BACKUP_DIR}/redis/dump_${DATE}.rdb"

if [ $? -eq 0 ]; then
    log "Redis backup completed: dump_${DATE}.rdb"
else
    error "Redis backup failed!"
fi

# -----------------------------------------------------------------------------
# Cleanup old backups
# -----------------------------------------------------------------------------
log "Cleaning up backups older than ${RETENTION_DAYS} days..."

find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete

log "Backup process completed!"
```

### 9.2 Restore Script

Tạo file `docker/scripts/restore.sh`:

```bash
#!/bin/bash
# =============================================================================
# RESTORE SCRIPT - PostgreSQL
# =============================================================================

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
echo "Backup file: $BACKUP_FILE"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Restoring database..."

gunzip -c "$BACKUP_FILE" | docker exec -i ressynt-postgres psql -U "${PGUSER}"

echo "Restore completed!"
```

### 9.3 Cron Job

```bash
# Add to crontab (crontab -e)
# Daily backup at 2:00 AM
0 2 * * * /path/to/docker/scripts/backup.sh >> /var/log/ressynt-backup.log 2>&1
```

---

## 10. Commands Reference

### 10.1 Deployment Commands

```bash
# =============================================================================
# BUILD & DEPLOY
# =============================================================================

# Build production image
docker compose -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (CAUTION: Data loss!)
docker compose -f docker-compose.prod.yml down -v

# =============================================================================
# DJANGO MANAGEMENT
# =============================================================================

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Django shell
docker compose -f docker-compose.prod.yml exec web python manage.py shell

# =============================================================================
# DATABASE
# =============================================================================

# PostgreSQL shell
docker compose -f docker-compose.prod.yml exec postgres psql -U ${PGUSER} -d ${PGDATABASE}

# Redis CLI
docker compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD}

# =============================================================================
# SSL CERTIFICATES (Let's Encrypt)
# =============================================================================

# Initial certificate request
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email your-email@example.com \
    --agree-tos --no-eff-email \
    -d your-domain.com -d www.your-domain.com

# Force renewal
docker compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# =============================================================================
# MAINTENANCE
# =============================================================================

# View container status
docker compose -f docker-compose.prod.yml ps

# View resource usage
docker stats

# Prune unused images/containers
docker system prune -af

# View container logs
docker logs ressynt-web --tail 100 -f
docker logs ressynt-celery-worker --tail 100 -f

# Restart specific service
docker compose -f docker-compose.prod.yml restart web

# Scale Celery workers
docker compose -f docker-compose.prod.yml up -d --scale celery_worker=3
```

### 10.2 Development Commands

```bash
# Start development environment
docker compose -f docker-compose.dev.yml up

# Rebuild after requirements change
docker compose -f docker-compose.dev.yml up --build

# Run tests
docker compose -f docker-compose.dev.yml exec web python manage.py test

# Access shell
docker compose -f docker-compose.dev.yml exec web bash
```

### 10.3 Troubleshooting

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' ressynt-web

# View environment variables
docker compose -f docker-compose.prod.yml exec web env

# Check network connectivity
docker compose -f docker-compose.prod.yml exec web ping postgres
docker compose -f docker-compose.prod.yml exec web ping redis

# View volume mounts
docker volume ls
docker volume inspect ressynt-prod_postgres_data

# Check image vulnerabilities (requires Docker Scout)
docker scout cves ressynt-web:latest
```

---

## Checklist triển khai

- [ ] Copy và cấu hình `.env.docker`
- [ ] Tạo thư mục data: `mkdir -p /data/ressynt/{postgres,redis,media,logs,nginx_logs,certbot/{conf,www}}`
- [ ] Cập nhật domain trong nginx config
- [ ] Build image: `docker compose -f docker-compose.prod.yml build`
- [ ] Start services: `docker compose -f docker-compose.prod.yml up -d`
- [ ] Request SSL certificate (xem commands reference)
- [ ] Run migrations: `docker exec ressynt-web python manage.py migrate`
- [ ] Create superuser
- [ ] Test health endpoint: `curl https://your-domain.com/health/`
- [ ] Setup backup cron job
- [ ] Configure monitoring (optional)

---

## Tài liệu liên quan

- [REDIS_CONFIGURATION.md](./REDIS_CONFIGURATION.md) - Hướng dẫn cấu hình Redis chi tiết
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Nginx Security](https://nginx.org/en/docs/http/configuring_https_servers.html)
