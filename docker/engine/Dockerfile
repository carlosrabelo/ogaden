# Multi-stage build
ARG SERVICE=engine

# Base stage
FROM python:3.12-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
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

# Engine stage
FROM base as engine

# Engine-specific configuration
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=5 \
    CMD python -m ogaden.healthcheck || exit 1

CMD ["ogaden-engine"]
