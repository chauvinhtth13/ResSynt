# Base image
FROM python:3.12-slim

# Metadata
LABEL maintainer="ressynt@example.com"
LABEL version="1.0"
LABEL description="ResSynt Multi-Study Dashboard"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # PostgreSQL client
    postgresql-client \
    libpq-dev \
    # Build tools
    gcc \
    g++ \
    make \
    # Utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user (security best practice)
RUN useradd -m -u 1000 django && \
    mkdir -p /app && \
    chown -R django:django /app

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY --chown=django:django . .

# Create necessary directories
RUN mkdir -p logs backups staticfiles mediafiles && \
    chown -R django:django logs backups staticfiles mediafiles

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "config.wsgi:application"]