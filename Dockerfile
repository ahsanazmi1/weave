# Weave Audit & Receipt Engine Dockerfile
# Production-ready container for CloudEvents subscriber and receipt management

# Build stage
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN uv pip install --system -e .

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    WEAVE_MODE=AUDIT \
    WEAVE_EXPLAIN_ENABLED=true

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r weave && useradd -r -g weave weave

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/

# Create data directory for receipts database
RUN mkdir -p data && chmod 755 data

# Set ownership
RUN chown -R weave:weave /app

# Switch to non-root user
USER weave

# Expose port
EXPOSE 8082

# Health check endpoints
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Default command
CMD ["python", "-m", "weave.subscriber"]
