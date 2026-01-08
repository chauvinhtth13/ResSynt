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
