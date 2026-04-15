# Multi-stage build
ARG SERVICE=dashboard

# Base stage
FROM python:3.12-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and requirements first for better layer caching
COPY pyproject.toml README.md LICENSE ./
COPY ogaden/ ogaden/

# Install Python dependencies
RUN pip install --no-cache-dir .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Dashboard stage
FROM base as dashboard

# Dashboard-specific configuration
EXPOSE 3501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3501/health || exit 1

CMD ["ogaden-dashboard"]
