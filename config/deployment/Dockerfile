# Multi-stage Dockerfile for OpenCode-Slack Agent Orchestration System
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r opencode && useradd -r -g opencode opencode

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-cov black flake8 mypy

# Copy source code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/sessions /app/data && \
    chown -R opencode:opencode /app

# Switch to non-root user
USER opencode

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command for development
CMD ["python", "src/server_secure.py", "--host", "0.0.0.0", "--port", "8080", "--environment", "development"]

# Production stage
FROM base as production

# Copy source code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /var/lib/opencode-slack/sessions \
             /var/lib/opencode-slack/data \
             /var/log/opencode-slack \
             /etc/opencode-slack && \
    chown -R opencode:opencode /var/lib/opencode-slack /var/log/opencode-slack /etc/opencode-slack /app

# Copy production configuration template
COPY .env.production /etc/opencode-slack/.env.production.template

# Switch to non-root user
USER opencode

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=60s --timeout=15s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Production command
CMD ["python", "src/server_secure.py", "--host", "0.0.0.0", "--port", "8080", "--environment", "production"]