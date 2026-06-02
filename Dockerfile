# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (gcc needed for sqlite-vec compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual env for easy copy
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

# Copy only the virtual env from builder (no gcc, no build tools)
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY sift/ sift/
COPY pages/ pages/

# Create workspace directory (data mounted via docker-compose volumes)
RUN mkdir -p /app/workspaces

# Default: run weekly digest
ENTRYPOINT ["python3", "sift/cli.py"]
CMD ["run"]
