# ==============================================================================
# Multi-Stage Production Dockerfile for KubeVora Backend Orchestrator
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Minimal Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KUBECONFIG=/home/appuser/.kube/config

# Install curl, ca-certificates, and the official kubectl binary (v1.30.0)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL -o /usr/local/bin/kubectl https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN useradd -m -u 10001 -s /bin/bash appuser

WORKDIR /app

# Copy python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY --chown=appuser:appuser . .

# Setup directory for kubeconfig with appropriate permissions
RUN mkdir -p /home/appuser/.kube && chown -R appuser:appuser /home/appuser/.kube

USER appuser

EXPOSE 8000

# Native health check against FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn orchestrator
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
